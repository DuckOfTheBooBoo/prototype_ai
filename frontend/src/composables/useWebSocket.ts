import { io, Socket } from 'socket.io-client'
import { ref, onMounted, onUnmounted } from 'vue'
import type { Prediction } from '@/types'

// WebSocket URL configuration - will be fetched from backend
const getWebSocketUrl = (): string => {
  // Check for environment variable first (for deployment)
  const envUrl = import.meta.env.VITE_WEBSOCKET_URL
  if (envUrl) {
    return envUrl
  }
  
  // Default to current origin with proper WebSocket path
  return '' // Will be fetched from /config endpoint
}

export function useWebSocket() {
  const socket = ref<Socket | null>(null)
  const isConnected = ref(false)
  const predictions = ref<Prediction[]>([])
  const streamComplete = ref(false)
  const configLoading = ref(true)
  const configError = ref<string | null>(null)

  const getOrCreateVisitorId = (): string => {
    let visitorId = localStorage.getItem('visitor_id')
    
    if (!visitorId) {
      // Generate UUID v4
      visitorId = crypto.randomUUID()
      localStorage.setItem('visitor_id', visitorId)
      console.log('Generated new visitor_id:', visitorId)
    } else {
      console.log('Using existing visitor_id:', visitorId)
    }
    
    return visitorId
  }

  const fetchConfig = async (): Promise<string | null> => {
    try {
      const response = await fetch('/config')
      if (!response.ok) {
        throw new Error('Failed to fetch config')
      }
      const config = await response.json()
      return config.websocket_url
    } catch (error) {
      console.error('Error fetching config:', error)
      configError.value = error instanceof Error ? error.message : 'Unknown error'
      return null
    }
  }

  const connect = async () => {
    configLoading.value = true
    
    try {
      // Fetch WebSocket URL from backend
      let wsUrl = await fetchConfig()
      
      // Fallback to environment variable or current origin
      if (!wsUrl) {
        const envUrl = import.meta.env.VITE_WEBSOCKET_URL
        if (envUrl) {
          wsUrl = envUrl
        } else {
          // Use current origin with default path
          wsUrl = '' // Let socket.io-client use default
        }
      }
      
      configLoading.value = false
      
      socket.value = io(wsUrl, {
        transports: ['websocket', 'polling'],
        autoConnect: true,
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
      })

      socket.value.on('connect', () => {
        isConnected.value = true
        console.log('Connected to server')
        
        // Send visitor_id to join/create stream
        const visitorId = getOrCreateVisitorId()
        socket.value?.emit('join_stream', { visitor_id: visitorId })
      })

      socket.value.on('stream_started', () => {
        console.log('New stream started for this visitor')
        streamComplete.value = false
      })
      
      socket.value.on('joined_existing_stream', () => {
        console.log('Joined existing stream (another tab is already streaming)')
      })

      socket.value.on('disconnect', () => {
        isConnected.value = false
        console.log('Disconnected from server')
      })

      socket.value.on('connected', () => {
        console.log('Server confirmed connection')
      })

      socket.value.on('prediction', (data: Prediction) => {
        predictions.value.push(data)
        saveToLocalStorage(data)
      })

      socket.value.on('stream_complete', (data) => {
        console.log(`Stream complete! Total transactions processed: ${data.total}`)
        console.log(`Message: ${data.message}`)
        streamComplete.value = true
      })
      
      socket.value.on('stream_error', (data) => {
        console.error('Stream error:', data.error)
      })
      
      socket.value.on('error', (data) => {
        console.error('WebSocket error:', data.message)
      })
      
    } catch (error) {
      configLoading.value = false
      configError.value = error instanceof Error ? error.message : 'Unknown error'
      console.error('Failed to connect:', error)
    }
  }

    socket.value.on('connect', () => {
      isConnected.value = true
      console.log('Connected to server')
      
      // Send visitor_id to join/create stream
      const visitorId = getOrCreateVisitorId()
      socket.value?.emit('join_stream', { visitor_id: visitorId })
    })

    socket.value.on('stream_started', () => {
      console.log('New stream started for this visitor')
      streamComplete.value = false
    })
    
    socket.value.on('joined_existing_stream', () => {
      console.log('Joined existing stream (another tab is already streaming)')
    })

    socket.value.on('disconnect', () => {
      isConnected.value = false
      console.log('Disconnected from server')
    })

    socket.value.on('connected', () => {
      console.log('Server confirmed connection')
    })

    socket.value.on('prediction', (data: Prediction) => {
      predictions.value.push(data)
      saveToLocalStorage(data)
    })

    socket.value.on('stream_complete', (data) => {
      console.log(`Stream complete! Total transactions processed: ${data.total}`)
      console.log(`Message: ${data.message}`)
      streamComplete.value = true
    })
    
    socket.value.on('stream_error', (data) => {
      console.error('Stream error:', data.error)
    })
    
    socket.value.on('error', (data) => {
      console.error('WebSocket error:', data.message)
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
    loadFromLocalStorage()
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    predictions,
    socket,
    streamComplete,
    configLoading,
    configError,
    reconnect: connect
  }
}
