# ============================================
# TRADE MONITOR - Check Active Trades & Performance
# ============================================

import json
import os
from datetime import datetime

def check_trades():
    """Check active trades and history"""
    print("\n" + "="*60)
    print("📊 SNIPER SYSTEM TRADE MONITOR")
    print("="*60)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check active trades
    if os.path.exists('active_trades.json'):
        with open('active_trades.json', 'r') as f:
            active = json.load(f)
        
        if active:
            print(f"\n🟢 ACTIVE TRADES: {len(active)}")
            print("-" * 40)
            for trade_id, trade in active.items():
                print(f"\n📈 {trade['symbol']} - {trade['type']}")
                print(f"   Entry: {trade['entry']:.5f}")
                print(f"   Stop: {trade['stop']:.5f}")
                print(f"   Targets: {trade['target1']:.5f} | {trade['target2']:.5f} | {trade['target3']:.5f}")
                print(f"   Risk: ${trade['risk_amount']:.2f}")
                print(f"   Status: {trade['status']}")
                print(f"   Hit Targets: {trade['hit_targets']}")
                print(f"   ID: {trade_id}")
        else:
            print("\n🟢 No active trades")
    else:
        print("\n🟢 No active trades file")
    
    # Check history
    if os.path.exists('trade_history.json'):
        with open('trade_history.json', 'r') as f:
            history = json.load(f)
        
        print(f"\n📜 TRADE HISTORY: {len(history)}")
        print("-" * 40)
        
        if history:
            # Calculate summary
            total_pnl = sum(t.get('pnl', 0) for t in history)
            wins = sum(1 for t in history if t.get('pnl', 0) > 0)
            losses = sum(1 for t in history if t.get('pnl', 0) < 0)
            win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
            
            print(f"\n📊 SUMMARY:")
            print(f"   Total P&L: ${total_pnl:.2f}")
            print(f"   Wins: {wins}")
            print(f"   Losses: {losses}")
            print(f"   Win Rate: {win_rate:.1f}%")
            
            # Show last 5 trades
            print(f"\n📋 LAST 5 TRADES:")
            print("-" * 40)
            for trade in history[-5:]:
                pnl = trade.get('pnl', 0)
                emoji = "✅" if pnl > 0 else "❌" if pnl < 0 else "⚪"
                close_reason = trade.get('close_reason', 'Closed')
                print(f"   {emoji} {trade['symbol']} - ${pnl:.2f} - {close_reason}")
                print(f"      Entry: {trade['entry']:.5f} → Close: {trade['close_price']:.5f}")
                print(f"      Pips: {trade.get('pips', 0):.1f}")
            
            # Best and worst trades
            best = max(history, key=lambda x: x.get('pnl', 0))
            worst = min(history, key=lambda x: x.get('pnl', 0))
            
            print(f"\n🏆 BEST TRADE: {best['symbol']} - ${best['pnl']:.2f}")
            print(f"📉 WORST TRADE: {worst['symbol']} - ${worst['pnl']:.2f}")
            
        else:
            print("\n📜 No trade history yet")
    else:
        print("\n📜 No trade history file")
    
    print("\n" + "="*60)

def clear_history():
    """Clear all trade history (use with caution)"""
    confirm = input("\n⚠️  WARNING: This will delete all trade history! Type 'yes' to confirm: ")
    if confirm.lower() == 'yes':
        if os.path.exists('active_trades.json'):
            os.remove('active_trades.json')
        if os.path.exists('trade_history.json'):
            os.remove('trade_history.json')
        print("✅ Trade history cleared!")
    else:
        print("❌ Operation cancelled")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'clear':
        clear_history()
    else:
        check_trades()
