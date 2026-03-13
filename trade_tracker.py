# trade_tracker.py
import json
import os
from datetime import datetime, timedelta
import requests

class TradeTracker:
    """Tracks all trades and sends updates"""
    
    def __init__(self, telegram):
        self.telegram = telegram
        self.trades_file = 'active_trades.json'
        self.history_file = 'trade_history.json'
        self.load_trades()
    
    def load_trades(self):
        """Load active trades from file"""
        if os.path.exists(self.trades_file):
            with open(self.trades_file, 'r') as f:
                self.active_trades = json.load(f)
        else:
            self.active_trades = {}
        
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = []
    
    def save_trades(self):
        """Save active trades to file"""
        with open(self.trades_file, 'w') as f:
            json.dump(self.active_trades, f, indent=2)
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def add_trade(self, signal, position, analysis):
        """Add a new trade to tracking"""
        trade_id = f"{signal['symbol']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        trade = {
            'id': trade_id,
            'symbol': signal['symbol'],
            'type': signal['type'],
            'entry': signal['entry_limit'],
            'stop': signal['stop'],
            'target1': signal['target1'],
            'target2': signal['target2'],
            'target3': signal['target3'],
            'lots': position['mini_lots'],
            'risk_amount': position['risk_amount'],
            'entry_time': datetime.now().isoformat(),
            'status': 'ACTIVE',
            'hit_targets': [],
            'rejection': signal.get('rejection_score', 0)
        }
        
        self.active_trades[trade_id] = trade
        self.save_trades()
        
        # Send confirmation
        msg = f"""
<b>📈 TRADE RECORDED</b>
━━━━━━━━━━━━━━━━━━━━━
<b>{'🔴' if 'SHORT' in signal['type'] else '🟢'} {signal['symbol']}</b>
Entry: {signal['entry_limit']:.5f}
Risk: ${position['risk_amount']:.2f}

<b>I'll alert you when:</b>
• TP1 Hit ✅
• TP2 Hit ✅
• TP3 Hit ✅
• Stop Hit ❌
━━━━━━━━━━━━━━━━━━━━━
"""
        self.telegram.send_message(msg)
    
    def check_trades(self, current_prices):
        """Check all active trades against current prices"""
        updates = []
        
        for trade_id, trade in list(self.active_trades.items()):
            symbol = trade['symbol']
            if symbol not in current_prices:
                continue
            
            current = current_prices[symbol]
            result = self.check_trade_status(trade, current)
            
            if result:
                updates.append(result)
                if trade['status'] == 'CLOSED':
                    del self.active_trades[trade_id]
        
        if updates:
            self.save_trades()
        
        return updates
    
    def check_trade_status(self, trade, current_price):
        """Check if trade hit any levels"""
        
        if trade['type'] == 'SHORT':
            # For shorts, price going DOWN is good
            if current_price <= trade['target1'] and 1 not in trade['hit_targets']:
                trade['hit_targets'].append(1)
                return self.target_hit(trade, 1, current_price)
            
            elif current_price <= trade['target2'] and 2 not in trade['hit_targets']:
                trade['hit_targets'].append(2)
                return self.target_hit(trade, 2, current_price)
            
            elif current_price <= trade['target3'] and 3 not in trade['hit_targets']:
                trade['hit_targets'].append(3)
                trade['status'] = 'CLOSED'
                return self.target_hit(trade, 3, current_price)
            
            elif current_price >= trade['stop']:
                trade['status'] = 'CLOSED'
                return self.stop_hit(trade, current_price)
        
        else:  # LONG
            if current_price >= trade['target1'] and 1 not in trade['hit_targets']:
                trade['hit_targets'].append(1)
                return self.target_hit(trade, 1, current_price)
            
            elif current_price >= trade['target2'] and 2 not in trade['hit_targets']:
                trade['hit_targets'].append(2)
                return self.target_hit(trade, 2, current_price)
            
            elif current_price >= trade['target3'] and 3 not in trade['hit_targets']:
                trade['hit_targets'].append(3)
                trade['status'] = 'CLOSED'
                return self.target_hit(trade, 3, current_price)
            
            elif current_price <= trade['stop']:
                trade['status'] = 'CLOSED'
                return self.stop_hit(trade, current_price)
        
        return None
    
    def target_hit(self, trade, target_num, current_price):
        """Handle target hit"""
        # Calculate profit
        if trade['type'] == 'SHORT':
            pips = (trade['entry'] - current_price) * 10000
            profit = pips * trade['lots']  # Simplified
        else:
            pips = (current_price - trade['entry']) * 10000
            profit = pips * trade['lots']
        
        msg = f"""
<b>✅ TARGET {target_num} HIT!</b>
━━━━━━━━━━━━━━━━━━━━━
<b>{'🔴' if 'SHORT' in trade['type'] else '🟢'} {trade['symbol']}</b>
Entry: {trade['entry']:.5f}
Target {target_num}: {current_price:.5f}
Profit: ${profit:.2f}

{'' if target_num == 3 else 'Still holding for next target...'}
━━━━━━━━━━━━━━━━━━━━━
"""
        return msg
    
    def stop_hit(self, trade, current_price):
        """Handle stop loss hit"""
        # Calculate loss
        if trade['type'] == 'SHORT':
            pips = (current_price - trade['entry']) * 10000
        else:
            pips = (trade['entry'] - current_price) * 10000
        
        loss = pips * trade['lots']
        
        msg = f"""
<b>❌ STOP LOSS HIT</b>
━━━━━━━━━━━━━━━━━━━━━
<b>{'🔴' if 'SHORT' in trade['type'] else '🟢'} {trade['symbol']}</b>
Entry: {trade['entry']:.5f}
Stop: {current_price:.5f}
Loss: ${loss:.2f}

Trade closed. Better luck next time!
━━━━━━━━━━━━━━━━━━━━━
"""
        return msg
    
    def weekly_report(self):
        """Generate weekly performance report"""
        # Filter trades from last 7 days
        week_ago = datetime.now() - timedelta(days=7)
        week_trades = [t for t in self.history 
                      if datetime.fromisoformat(t['close_time']) > week_ago]
        
        wins = [t for t in week_trades if t['pnl'] > 0]
        losses = [t for t in week_trades if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in week_trades)
        win_rate = len(wins) / len(week_trades) * 100 if week_trades else 0
        
        msg = f"""
<b>📊 WEEKLY PERFORMANCE</b>
━━━━━━━━━━━━━━━━━━━━━
<b>Trades:</b> {len(week_trades)}
<b>Wins:</b> {len(wins)}
<b>Losses:</b> {len(losses)}
<b>Win Rate:</b> {win_rate:.1f}%
<b>Total P&L:</b> ${total_pnl:.2f}

<b>Best Trade:</b> ${max([t['pnl'] for t in week_trades] + [0]):.2f}
<b>Worst Trade:</b> ${min([t['pnl'] for t in week_trades] + [0]):.2f}
━━━━━━━━━━━━━━━━━━━━━
"""
        return msg
