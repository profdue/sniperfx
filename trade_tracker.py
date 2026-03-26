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
Stop: {signal['stop']:.5f}
Risk: ${position['risk_amount']:.2f}
Target 1: {signal['target1']:.5f}
Target 2: {signal['target2']:.5f}
Target 3: {signal['target3']:.5f}

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
                    # Move to history before deleting
                    self.move_to_history(trade_id, trade)
                    del self.active_trades[trade_id]
        
        if updates:
            self.save_trades()
        
        return updates
    
    def move_to_history(self, trade_id, trade):
        """Move closed trade to history with P&L calculation"""
        # Calculate final P&L
        if trade['status'] == 'CLOSED':
            # Get closing price from the last target hit or stop
            close_price = trade.get('close_price', None)
            
            if close_price:
                if trade['type'] == 'SHORT':
                    pips = (trade['entry'] - close_price) * 10000
                else:  # LONG
                    pips = (close_price - trade['entry']) * 10000
                
                pnl = pips * trade['lots']
                
                # Determine closing reason
                if 'hit_targets' and trade['hit_targets']:
                    if 3 in trade['hit_targets']:
                        close_reason = f"TP3 HIT (Target {max(trade['hit_targets'])})"
                    else:
                        close_reason = f"TARGET {max(trade['hit_targets'])} HIT"
                else:
                    close_reason = "STOP LOSS"
                
                history_entry = {
                    'id': trade_id,
                    'symbol': trade['symbol'],
                    'type': trade['type'],
                    'entry': trade['entry'],
                    'stop': trade['stop'],
                    'target1': trade['target1'],
                    'target2': trade['target2'],
                    'target3': trade['target3'],
                    'lots': trade['lots'],
                    'risk_amount': trade['risk_amount'],
                    'entry_time': trade['entry_time'],
                    'close_time': datetime.now().isoformat(),
                    'close_price': close_price,
                    'close_reason': close_reason,
                    'hit_targets': trade['hit_targets'],
                    'pips': pips,
                    'pnl': pnl,
                    'rejection': trade.get('rejection', 0)
                }
                
                self.history.append(history_entry)
                
                # Send final result message
                self.send_final_result(history_entry)
    
    def send_final_result(self, trade):
        """Send final trade result with P&L"""
        if trade['pnl'] >= 0:
            emoji = "✅"
            result_text = "PROFIT"
        else:
            emoji = "❌"
            result_text = "LOSS"
        
        msg = f"""
<b>{emoji} TRADE CLOSED - {result_text}</b>
━━━━━━━━━━━━━━━━━━━━━
<b>{'🔴' if 'SHORT' in trade['type'] else '🟢'} {trade['symbol']}</b>
<b>Result:</b> {result_text}
<b>P&L:</b> ${trade['pnl']:.2f}
<b>Pips:</b> {trade['pips']:.1f} pips

<b>Entry:</b> {trade['entry']:.5f}
<b>Close:</b> {trade['close_price']:.5f}
<b>Reason:</b> {trade['close_reason']}

<b>Duration:</b> {self.calculate_duration(trade['entry_time'], trade['close_time'])}
━━━━━━━━━━━━━━━━━━━━━
"""
        self.telegram.send_message(msg)
    
    def calculate_duration(self, start_time, end_time):
        """Calculate trade duration in readable format"""
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        duration = end - start
        
        hours = duration.total_seconds() / 3600
        
        if hours < 1:
            minutes = duration.total_seconds() / 60
            return f"{minutes:.0f} minutes"
        elif hours < 24:
            return f"{hours:.1f} hours"
        else:
            return f"{hours/24:.1f} days"
    
    def check_trade_status(self, trade, current_price):
        """Check if trade hit any levels"""
        
        if trade['type'] == 'SHORT':
            # For shorts, price going DOWN is good
            if current_price <= trade['target1'] and 1 not in trade['hit_targets']:
                trade['hit_targets'].append(1)
                trade['close_price'] = current_price
                return self.target_hit(trade, 1, current_price)
            
            elif current_price <= trade['target2'] and 2 not in trade['hit_targets']:
                trade['hit_targets'].append(2)
                trade['close_price'] = current_price
                return self.target_hit(trade, 2, current_price)
            
            elif current_price <= trade['target3'] and 3 not in trade['hit_targets']:
                trade['hit_targets'].append(3)
                trade['status'] = 'CLOSED'
                trade['close_price'] = current_price
                return self.target_hit(trade, 3, current_price)
            
            elif current_price >= trade['stop']:
                trade['status'] = 'CLOSED'
                trade['close_price'] = current_price
                return self.stop_hit(trade, current_price)
        
        else:  # LONG
            if current_price >= trade['target1'] and 1 not in trade['hit_targets']:
                trade['hit_targets'].append(1)
                trade['close_price'] = current_price
                return self.target_hit(trade, 1, current_price)
            
            elif current_price >= trade['target2'] and 2 not in trade['hit_targets']:
                trade['hit_targets'].append(2)
                trade['close_price'] = current_price
                return self.target_hit(trade, 2, current_price)
            
            elif current_price >= trade['target3'] and 3 not in trade['hit_targets']:
                trade['hit_targets'].append(3)
                trade['status'] = 'CLOSED'
                trade['close_price'] = current_price
                return self.target_hit(trade, 3, current_price)
            
            elif current_price <= trade['stop']:
                trade['status'] = 'CLOSED'
                trade['close_price'] = current_price
                return self.stop_hit(trade, current_price)
        
        return None
    
    def target_hit(self, trade, target_num, current_price):
        """Handle target hit"""
        # Calculate profit so far
        if trade['type'] == 'SHORT':
            pips = (trade['entry'] - current_price) * 10000
            profit = pips * trade['lots']
        else:
            pips = (current_price - trade['entry']) * 10000
            profit = pips * trade['lots']
        
        msg = f"""
<b>✅ TARGET {target_num} HIT!</b>
━━━━━━━━━━━━━━━━━━━━━
<b>{'🔴' if 'SHORT' in trade['type'] else '🟢'} {trade['symbol']}</b>
Entry: {trade['entry']:.5f}
Target {target_num}: {current_price:.5f}
Profit So Far: ${profit:.2f}
Pips: {pips:.1f}

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
Pips: {pips:.1f}

Trade closed. Better luck next time!
━━━━━━━━━━━━━━━━━━━━━
"""
        return msg
    
    def get_performance_stats(self):
        """Get overall performance statistics"""
        if not self.history:
            return "No trades in history yet."
        
        total_trades = len(self.history)
        winning_trades = [t for t in self.history if t['pnl'] > 0]
        losing_trades = [t for t in self.history if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in self.history)
        win_rate = len(winning_trades) / total_trades * 100 if total_trades else 0
        
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        # Calculate max drawdown
        cumulative = 0
        peak = 0
        max_drawdown = 0
        for trade in self.history:
            cumulative += trade['pnl']
            if cumulative > peak:
                peak = cumulative
            drawdown = peak - cumulative
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        msg = f"""
<b>📊 OVERALL PERFORMANCE</b>
━━━━━━━━━━━━━━━━━━━━━
<b>Total Trades:</b> {total_trades}
<b>Winning Trades:</b> {len(winning_trades)}
<b>Losing Trades:</b> {len(losing_trades)}
<b>Win Rate:</b> {win_rate:.1f}%

<b>Total P&L:</b> ${total_pnl:.2f}
<b>Average Win:</b> ${avg_win:.2f}
<b>Average Loss:</b> ${avg_loss:.2f}
<b>Profit Factor:</b> {abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)):.2f} if losing_trades else 'N/A'}

<b>Max Drawdown:</b> ${max_drawdown:.2f}
━━━━━━━━━━━━━━━━━━━━━
"""
        return msg
    
    def weekly_report(self):
        """Generate weekly performance report"""
        # Filter trades from last 7 days
        week_ago = datetime.now() - timedelta(days=7)
        week_trades = [t for t in self.history 
                      if datetime.fromisoformat(t['close_time']) > week_ago]
        
        if not week_trades:
            return "No trades in the last 7 days."
        
        wins = [t for t in week_trades if t['pnl'] > 0]
        losses = [t for t in week_trades if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in week_trades)
        win_rate = len(wins) / len(week_trades) * 100 if week_trades else 0
        
        # Calculate best and worst trades
        best_trade = max(week_trades, key=lambda x: x['pnl']) if week_trades else None
        worst_trade = min(week_trades, key=lambda x: x['pnl']) if week_trades else None
        
        msg = f"""
<b>📊 WEEKLY PERFORMANCE</b>
━━━━━━━━━━━━━━━━━━━━━
<b>Trades:</b> {len(week_trades)}
<b>Wins:</b> {len(wins)}
<b>Losses:</b> {len(losses)}
<b>Win Rate:</b> {win_rate:.1f}%
<b>Total P&L:</b> ${total_pnl:.2f}

<b>Best Trade:</b> ${best_trade['pnl']:.2f} ({best_trade['symbol']}) if best_trade else 'N/A'}
<b>Worst Trade:</b> ${worst_trade['pnl']:.2f} ({worst_trade['symbol']}) if worst_trade else 'N/A'}
━━━━━━━━━━━━━━━━━━━━━
"""
        return msg
