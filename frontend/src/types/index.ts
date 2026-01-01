export interface Prediction {
  TransactionID: number
  TransactionAmt: number
  fraud_probability: number
  risk_level: 'LOW' | 'HIGH' | 'CRITICAL'
  status: 'APPROVE' | 'DENY'
  timestamp: string
}

export interface WebSocketMessage {
  type: 'prediction' | 'connected' | 'disconnected'
  data?: Prediction
}

export interface Stats {
  total: number
  flagged: number
  approved: number
  denied: number
  critical: number
  high: number
  low: number
}

export interface TransactionFilters {
  riskLevel: 'ALL' | 'CRITICAL' | 'HIGH' | 'LOW'
  status: 'ALL' | 'APPROVE' | 'DENY'
  dateRange: {
    start: any
    end: any
  }
  timeRange: {
    startHour: number
    startMinute: number
    endHour: number
    endMinute: number
  }
}
