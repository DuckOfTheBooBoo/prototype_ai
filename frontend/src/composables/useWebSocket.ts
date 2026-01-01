import { io, Socket } from 'socket.io-client'
import { ref, onMounted, onUnmounted } from 'vue'
import type { Prediction } from '@/types'

export function useWebSocket() {
  const socket = ref<Socket | null>(null)
  const isConnected = ref(false)
  const predictions = ref<Prediction[]>([])
  const streamComplete = ref(false)

  const getOrCreateVisitorId = (): string => {
    let visitorId = localStorage.getItem('visitor_id')
    if (!visitorId) {
      visitorId = `visitor_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      localStorage.setItem('visitor_id', visitorId)
    }
    return visitorId
  }

  const connect = async () => {
    console.log('🟡 [WS] === STARTING WEBSOCKET CONNECTION ===')
    console.log('🟢 [WS] Step 1: Constructing WebSocket URL from current origin...')

    // Construct WebSocket URL directly from current origin
    const protocol = window.location.protocol.replace('http:', 'ws:').replace('https:', 'wss:')
    const wsUrl = `${protocol}//${window.location.host}/socket.io`

    console.log('🟢 [WS] WebSocket URL constructed:', wsUrl)
    console.log('🟢 [WS] Page origin:', window.location.origin)
    console.log('🟢 [WS] Page protocol:', window.location.protocol)
    console.log('🟢 [WS] Page hostname:', window.location.host)

    socket.value = io(wsUrl, {
      transports: ['websocket', 'polling'],
      autoConnect: true,
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000
    })

    console.log('🟢 [WS] Step 2: Socket.IO client created, autoConnect=true, waiting for connection...')

    socket.value.on('connect', () => {
      console.log('✅ [WS] Step 3: CONNECTED TO SERVER!')
      console.log('✅ [WS] Socket ID:', socket.value?.id)
      isConnected.value = true

      const visitorId = getOrCreateVisitorId()
      console.log('🟢 [WS] Step 4: Joining stream with visitor_id:', visitorId)
      socket.value?.emit('join_stream', { visitor_id: visitorId })
      console.log('🟢 [WS] Sent join_stream event')
    })

    socket.value.on('stream_started', () => {
      console.log('✅ [WS] Step 5: Stream started for this visitor')
      streamComplete.value = false
    })

    socket.value.on('joined_existing_stream', () => {
      console.log('✅ [WS] Step 5b: Joined existing stream (another tab is already streaming)')
    })

    socket.value.on('disconnect', () => {
      console.log('🔴 [WS] DISCONNECTED from server')
      isConnected.value = false
    })

    socket.value.on('connected', () => {
      console.log('✅ [WS] Server confirmed connection')
    })

    socket.value.on('prediction', (data: Prediction) => {
      console.log('📊 [WS] Received prediction #', predictions.value.length + 1, ':', data)
      predictions.value.push(data)
      saveToLocalStorage(data)
    })

    socket.value.on('stream_complete', (data) => {
      console.log(`✅ [WS] Step 6: Stream complete! Total: ${data.total}`)
      console.log(`✅ [WS] Message: ${data.message}`)
      streamComplete.value = true
    })

    socket.value.on('stream_error', (data) => {
      console.error('🔴 [WS] Stream error:', data.error)
    })

    socket.value.on('error', (data) => {
      console.error('🔴 [WS] Socket.IO error:', data.message)
    })
  }

  const saveToLocalStorage = (prediction: Prediction) => {
    try {
      const stored = localStorage.getItem('predictions')
      const all = stored ? JSON.parse(stored) : []
      all.push(prediction)
      localStorage.setItem('predictions', JSON.stringify(all))
    } catch (e) {
      console.error('Error saving to localStorage:', e)
    }
  }

  const loadFromLocalStorage = () => {
    try {
      const stored = localStorage.getItem('predictions')
      if (stored) {
        predictions.value = JSON.parse(stored)
      }
    } catch (e) {
      console.error('Error loading from localStorage:', e)
    }
  }

  const disconnect = () => {
    socket.value?.disconnect()
  }

  onMounted(() => {
    console.log('🟡 [WS] === COMPONENT MOUNTED ===')
    console.log('🟢 [WS] Step 0: Loading cached predictions from localStorage...')
    loadFromLocalStorage()
    console.log('🟢 [WS] Step 0a: Cached predictions loaded:', predictions.value.length)
    connect()
  })

  onUnmounted(() => {
    console.log('🟡 [WS] === COMPONENT UNMOUNTED ===')
    console.log('🟠 [WS] Disconnecting WebSocket...')
    disconnect()
  })

  return {
    isConnected,
    predictions,
    socket,
    streamComplete,
    reconnect: connect
  }
}
