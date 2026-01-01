# Session-Based WebSocket Streaming - Implementation Summary

## Overview
Successfully implemented per-visitor WebSocket streaming that allows each visitor to receive fresh transaction data on every visit, while efficiently sharing streams across multiple browser tabs.

---

## ✅ What Was Changed

### Backend Changes (`app.py`)

#### 1. **Global State Management**
- **Removed:**
  - `streaming_active` (global flag)
  - `streaming_thread` (global thread reference)
  
- **Added:**
  - `active_streams = {}` - Tracks active streams per visitor_id
  - `socket_to_visitor = {}` - Maps socket IDs to visitor IDs

#### 2. **WebSocket Connection Handling**

**`@socketio.on('connect')` (app.py:100-104)**
- Simplified to just acknowledge connection
- Removed automatic stream start

**`@socketio.on('join_stream')` (app.py:107-137)** [NEW]
- Accepts `visitor_id` from client
- Maps socket to visitor
- Joins Socket.IO room for the visitor
- Creates new stream OR joins existing stream
- Emits appropriate status events

**`@socketio.on('disconnect')` (app.py:140-164)**
- Looks up visitor from socket mapping
- Removes socket from visitor's stream
- Marks stream for cleanup if last socket
- Cleans up socket-to-visitor mapping

#### 3. **Streaming Logic**

**`stream_predictions(visitor_id)` (app.py:167-227)**
- **Parameters:** Now accepts `visitor_id` (was parameterless)
- **File Paths:** Fixed to use correct paths:
  - `./content/small_test_transaction.csv` (1,000 rows)
  - `./content/ieee-fraud-detection/test_identity.csv` (141,907 rows)
- **Timing:** Random delay between 0.5-2.5 seconds (avg ~1.5s = ~25 min total)
- **Room Broadcasting:** Emits to visitor's room, not globally
- **Events Emitted:**
  - `prediction` - Each transaction result (to room)
  - `stream_complete` - When all transactions processed (to room)
  - `stream_error` - If error occurs (to room)
- **Cleanup:** Removes stream from `active_streams` on completion/error

---

### Frontend Changes (`frontend/src/composables/useWebSocket.ts`)

#### 1. **New State Variables**
- `streamComplete` - Reactive ref to track stream completion

#### 2. **New Helper Function**
**`getOrCreateVisitorId()` (line 11-23)**
- Checks localStorage for `visitor_id`
- Generates UUID v4 if not found (`crypto.randomUUID()`)
- Saves to localStorage
- Returns the visitor_id

#### 3. **Updated Connection Logic**
**`connect()` function**
- On `'connect'` event (line 29-37):
  - Gets/creates visitor_id
  - Emits `'join_stream'` with visitor_id

#### 4. **New Event Handlers**
- `'stream_started'` - New stream created
- `'joined_existing_stream'` - Joined existing stream (another tab)
- `'stream_complete'` - Stream finished, logs total transactions
- `'stream_error'` - Stream encountered error
- `'error'` - General WebSocket error

#### 5. **Exported Values**
- Added `streamComplete` to return object

---

## 🎯 How It Works

### Single Visitor, First Visit
```
1. User opens page
2. Frontend generates visitor_id: "abc-123" → saves to localStorage
3. WebSocket connects
4. Frontend sends: join_stream({ visitor_id: "abc-123" })
5. Backend creates new stream for visitor "abc-123"
6. Backend emits: stream_started
7. User receives ~1,000 transactions over ~20-25 minutes
8. Backend emits: stream_complete
9. Console logs: "Stream complete! Total transactions: 1000"
```

### Same Visitor, Page Refresh
```
1. User refreshes page
2. Frontend reads visitor_id: "abc-123" from localStorage
3. WebSocket connects (new socket)
4. Frontend sends: join_stream({ visitor_id: "abc-123" })
5. Backend: Previous stream already completed/cleaned up
6. Backend creates FRESH NEW stream for visitor "abc-123"
7. User receives all 1,000 transactions again (fresh start)
```

### Same Visitor, Multiple Tabs
```
Tab 1:
1. Opens → generates visitor_id: "abc-123"
2. Connects → Backend starts stream for "abc-123"
3. Receives predictions

Tab 2 (opened later):
1. Opens → reads SAME visitor_id: "abc-123" from localStorage
2. Connects → Backend sees stream already exists
3. Backend emits: joined_existing_stream
4. Receives SAME predictions as Tab 1 (synchronized)

Both tabs receive identical data at the same time!

If Tab 1 closes:
- Tab 2 continues receiving data normally

If both tabs close:
- Backend marks stream for cleanup
- Stream stops on next iteration
```

### Different Visitors
```
Visitor A: visitor_id "abc-123" → Stream A (independent)
Visitor B: visitor_id "xyz-789" → Stream B (independent)

Both streams run completely independently.
```

---

## 📊 Timing & Performance

### Data Stats
- **Transactions:** 1,000 rows (from small_test_transaction.csv)
- **Random Delay:** 0.5 to 2.5 seconds per transaction
- **Average Delay:** ~1.5 seconds
- **Expected Duration:** ~18-25 minutes (due to randomness)
- **Progress Logs:** Every 100 transactions

### Resource Usage (per visitor)
- **Memory:** ~2-3 MB per active stream
- **Network:** ~0.5 KB per prediction
- **Total per demo:** ~500 KB over 20 minutes

### Scalability
- **Current design:** Perfect for 1-10 concurrent visitors
- **Your use case:** 1-2 visitors per week = ✅ Excellent fit

---

## 🧪 Testing Instructions

### Test 1: Fresh Stream on Page Refresh
```bash
1. Open http://localhost:3000 in browser
2. Open browser DevTools → Console
3. Look for: "Generated new visitor_id: <uuid>"
4. Watch predictions streaming in
5. Refresh the page (F5 or Ctrl+R)
6. Look for: "Using existing visitor_id: <same-uuid>"
7. Look for: "New stream started for this visitor"
8. Verify: Counter resets, fresh data streams again
```

**Expected Console Output:**
```
Connected to server
Generated new visitor_id: a1b2c3d4-e5f6-...
Server confirmed connection
New stream started for this visitor

[after ~20 minutes]
Stream complete! Total transactions processed: 1000
Message: All transactions processed
```

### Test 2: Multiple Tabs Share Same Stream
```bash
1. Clear localStorage (DevTools → Application → Local Storage → Clear All)
2. Open Tab 1: http://localhost:3000
3. Console shows: "Generated new visitor_id: <uuid>"
4. Console shows: "New stream started"
5. Wait for a few predictions to come in
6. Open Tab 2: http://localhost:3000 (same browser)
7. In Tab 2 console:
   - "Using existing visitor_id: <same-uuid>"
   - "Joined existing stream (another tab is already streaming)"
8. Verify: Both tabs show SAME predictions at SAME time
9. Close Tab 1
10. Verify: Tab 2 continues receiving predictions normally
```

### Test 3: Backend Stream Management
```bash
# Terminal 1: Run backend with verbose logging
python app.py

# Expected logs on first visitor:
Socket connected: <sid1>
Started new stream for visitor <visitor_id>
Loading test data for visitor <visitor_id>...
Merging transaction and identity data...
Streaming 1000 predictions for visitor <visitor_id>...
Visitor <visitor_id>: Processed 100/1000 transactions
Visitor <visitor_id>: Processed 200/1000 transactions
...
Stream complete for visitor <visitor_id>!
Cleaned up stream for visitor <visitor_id>
Socket disconnected: <sid1>

# When second tab opens:
Socket connected: <sid2>
Socket <sid2> joined existing stream for visitor <visitor_id>

# When both tabs close:
Last socket disconnected, marking stream <visitor_id> for cleanup
Stream <visitor_id> stopped early (cleanup requested)
```

### Test 4: Visitor ID Persistence
```bash
1. Open page → note visitor_id in console
2. Close browser completely
3. Reopen browser → open page again
4. Console should show: "Using existing visitor_id: <same-id>"
5. Stream starts fresh even with same visitor_id ✅

To test new visitor:
1. DevTools → Application → Local Storage
2. Delete 'visitor_id' entry
3. Refresh page
4. Console shows: "Generated new visitor_id: <new-uuid>"
5. This simulates a new visitor ✅
```

### Test 5: Stream Completion
```bash
1. Open page and wait ~20-25 minutes (or reduce delay for testing)
2. Watch console for final message:
   "Stream complete! Total transactions processed: 1000"
3. Backend log should show:
   "Stream complete for visitor <visitor_id>!"
   "Cleaned up stream for visitor <visitor_id>"
4. Verify no more predictions arrive ✅
```

---

## 🔧 Configuration & Adjustments

### Adjust Demo Duration
In `app.py:206`, change the random delay range:

```python
# Current: ~20-25 minutes for 1000 transactions
delay = random.uniform(0.5, 2.5)

# For faster testing: ~5-8 minutes
delay = random.uniform(0.2, 0.8)

# For exactly 20 minutes: ~1.2 seconds avg
delay = random.uniform(0.8, 1.6)

# For slower demo: ~30-40 minutes
delay = random.uniform(1.5, 3.5)
```

### Change Progress Log Frequency
In `app.py:209`, adjust logging interval:

```python
# Current: Log every 100 transactions
if (idx + 1) % 100 == 0:

# More frequent: Every 50 transactions
if (idx + 1) % 50 == 0:

# Less frequent: Every 200 transactions  
if (idx + 1) % 200 == 0:
```

---

## 🚀 Running the Application

### Backend
```bash
cd /var/mnt/nvme0n1p3/Users/pc/Datas/Programming/ngampus/prototype_ai
python app.py
```

### Frontend
```bash
cd frontend
npm install  # if needed
npm run dev
```

### Expected URLs
- Backend: http://localhost:5000
- Frontend: http://localhost:3000 (or as configured in Vite)

---

## ✅ Implementation Checklist

- [x] Backend: Remove global streaming state
- [x] Backend: Add per-visitor stream tracking
- [x] Backend: Implement `join_stream` handler
- [x] Backend: Update disconnect handler with cleanup
- [x] Backend: Refactor `stream_predictions` with visitor_id
- [x] Backend: Add room-based broadcasting
- [x] Backend: Fix CSV file paths
- [x] Backend: Add stream_complete event
- [x] Frontend: Add visitor_id generation (crypto.randomUUID)
- [x] Frontend: Store visitor_id in localStorage
- [x] Frontend: Send visitor_id on connect
- [x] Frontend: Handle stream lifecycle events
- [x] Frontend: Export streamComplete state
- [ ] Testing: Verify fresh stream on refresh
- [ ] Testing: Verify multiple tabs share stream

---

## 📝 Notes

### Browser Compatibility
- `crypto.randomUUID()` requires:
  - HTTPS context OR localhost
  - Modern browsers (Chrome 92+, Firefox 95+, Safari 15.4+)
  
If targeting older browsers, replace with:
```typescript
// Alternative UUID generation
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}
```

### Socket.IO Rooms
- Rooms are automatically managed by Socket.IO
- `join_room(visitor_id)` adds socket to room
- `emit(..., room=visitor_id)` broadcasts to all sockets in room
- When all sockets disconnect, room is auto-cleaned

### Error Handling
- Connection drops: Other tabs continue streaming
- All tabs close: Stream marked for cleanup, stops gracefully
- CSV file not found: Emits `stream_error` to client
- Prediction errors: Logged but stream continues

---

## 🎉 Success Criteria

Implementation is successful if:
1. ✅ Each visitor gets fresh data on every page load
2. ✅ Multiple tabs from same visitor share one stream
3. ✅ Streams cleanup properly when visitors leave
4. ✅ ~1000 transactions stream over ~20-25 minutes
5. ✅ Console logs "Stream complete" when done
6. ✅ No global streaming conflicts between visitors

---

## 🐛 Troubleshooting

### Issue: "visitor_id required" error
**Cause:** Frontend not sending visitor_id  
**Fix:** Check console for visitor_id generation, verify emit payload

### Issue: Multiple streams for same visitor
**Cause:** localStorage not persisting  
**Fix:** Check browser privacy settings, ensure cookies/storage enabled

### Issue: Predictions not appearing
**Cause:** CSV file path incorrect  
**Fix:** Verify files exist at:
- `./content/small_test_transaction.csv`
- `./content/ieee-fraud-detection/test_identity.csv`

### Issue: Stream never completes
**Cause:** Random delay too high  
**Fix:** Reduce delay range in app.py:206

### Issue: "crypto is not defined"
**Cause:** Running on HTTP (not localhost)  
**Fix:** Use localhost OR implement alternative UUID function

---

## 📚 Related Files

### Modified Files
- `app.py` - Backend streaming logic
- `frontend/src/composables/useWebSocket.ts` - Frontend WebSocket handling

### Data Files (unchanged)
- `content/small_test_transaction.csv` - 1,000 test transactions
- `content/ieee-fraud-detection/test_identity.csv` - Identity data

### Configuration Files (unchanged)
- `frontend/vite.config.ts` - Frontend dev server
- `requirements.txt` - Python dependencies
- `frontend/package.json` - Node dependencies

---

## 🎯 Next Steps

1. **Test thoroughly** using the testing instructions above
2. **Adjust timing** if needed (see Configuration section)
3. **Monitor performance** during actual demo sessions
4. **Consider enhancements:**
   - Add UI indicator for stream completion
   - Show progress bar (X/1000 transactions)
   - Add "Reset Data" button to clear localStorage
   - Display visitor_id in UI for debugging

---

## 📞 Questions?

If you encounter any issues or need clarification:
1. Check the console logs (both frontend and backend)
2. Verify file paths are correct
3. Ensure WebSocket connection is established
4. Check localStorage for visitor_id
5. Review server logs for stream lifecycle events

**Happy Testing! 🚀**
