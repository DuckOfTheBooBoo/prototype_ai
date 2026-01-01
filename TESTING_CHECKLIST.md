# Quick Testing Checklist

## ✅ Implementation Complete!

All code changes have been successfully implemented. Here's what to do next:

## 1. Start the Backend

```bash
cd /var/mnt/nvme0n1p3/Users/pc/Datas/Programming/ngampus/prototype_ai
python app.py
```

**Expected output:**
```
 * Running on http://0.0.0.0:5000
```

## 2. Start the Frontend

```bash
cd frontend
npm run dev
```

**Expected output:**
```
VITE ready in XXX ms
Local: http://localhost:3000
```

## 3. Quick Manual Tests

### Test A: Single Visitor Fresh Stream

1. Open browser to `http://localhost:3000`
2. Open DevTools Console (F12)
3. Look for these messages:
   ```
   Connected to server
   Generated new visitor_id: <some-uuid>
   New stream started for this visitor
   ```
4. Watch predictions appear in the UI
5. After a few predictions, **refresh the page** (F5)
6. Look for:
   ```
   Using existing visitor_id: <same-uuid>
   New stream started for this visitor
   ```
7. ✅ **PASS if:** Counter resets and stream starts from beginning

### Test B: Multiple Tabs Same Stream

1. With page still open from Test A
2. Open **second tab** to `http://localhost:3000`
3. In the second tab's console, look for:
   ```
   Using existing visitor_id: <same-uuid>
   Joined existing stream (another tab is already streaming)
   ```
4. ✅ **PASS if:** Both tabs show the same predictions at the same time

### Test C: Backend Logs

Check your backend terminal for:
```
Socket connected: <socket-id-1>
Started new stream for visitor <visitor-id>
Loading test data for visitor <visitor-id>...
Streaming 1000 predictions for visitor <visitor-id>...
Visitor <visitor-id>: Processed 100/1000 transactions
```

When you open second tab:
```
Socket connected: <socket-id-2>
Socket <socket-id-2> joined existing stream for visitor <visitor-id>
```

## 4. Verify Files

Check that these files exist and have content:
```bash
ls -lh content/small_test_transaction.csv
ls -lh content/ieee-fraud-detection/test_identity.csv
```

Both should exist and have data.

## 5. Optional: Test with Python Script

```bash
# Install dependency if needed
pip install python-socketio[client] requests

# Run test script
python test_streaming.py
```

## 🎯 What Should Happen

### Expected Behavior

1. **First visit**: Generate visitor_id → Start fresh stream
2. **Page refresh**: Use same visitor_id → Start NEW fresh stream (from beginning)
3. **Multiple tabs**: Share same stream (synchronized)
4. **Close all tabs**: Stream cleanup happens automatically
5. **After ~20-25 min**: Console shows "Stream complete! Total: 1000"

### Key Features Working

- ✅ Each visitor gets isolated stream
- ✅ Same visitor on refresh gets fresh data
- ✅ Multiple tabs share one stream efficiently
- ✅ Clean resource cleanup when leaving
- ✅ Random delays (0.5-2.5s) for realistic demo
- ✅ Stream complete notification

## 🐛 If Something Doesn't Work

### Backend won't start
```bash
# Check if port 5000 is already in use
lsof -i :5000

# If occupied, kill the process or change port in app.py
```

### Frontend won't start
```bash
# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### No predictions appearing
1. Check backend terminal for errors
2. Check browser console for WebSocket connection errors
3. Verify CSV files exist at correct paths
4. Check browser Network tab - should see WebSocket connection

### "crypto is not defined" in browser
- Make sure you're accessing via `localhost` (not IP address)
- Or use alternative UUID generation (see IMPLEMENTATION_SUMMARY.md)

## 📚 Documentation

For detailed information, see:
- **IMPLEMENTATION_SUMMARY.md** - Complete implementation details and advanced testing

## 🎉 Success!

If you see predictions streaming in and the console shows correct messages, everything is working! 

The system is now ready for your demo reviewers. Each visitor will get their own fresh stream, and it will handle 1-2 visitors per week perfectly.
