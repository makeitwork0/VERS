import curses
import sqlite3
import json
import time
import os
from datetime import datetime

DB_PATH = os.path.join("data", "vers_data.db")

def get_sys_load():
    """Gets the system load average (1, 5, 15 min) for Linux/Pi."""
    try:
        with open('/proc/loadavg', 'r') as f:
            return " ".join(f.read().split()[:3])
    except:
        return "N/A"

def get_sys_mem():
    """Gets system memory usage for Linux/Pi."""
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        mem_total = int(lines[0].split()[1])
        mem_avail = int(lines[2].split()[1])
        used = mem_total - mem_avail
        percent = (used / mem_total) * 100
        return f"{used/1024:.0f}MB/{mem_total/1024:.0f}MB ({percent:.1f}%)"
    except:
        return "N/A"

def get_db_data():
    """Fetches the latest state for each node and recent critical alerts."""
    if not os.path.exists(DB_PATH):
        return {}, []
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get latest payload per device
        c.execute('''
            SELECT device_id, payload, timestamp
            FROM sensor_logs
            WHERE id IN (SELECT MAX(id) FROM sensor_logs GROUP BY device_id)
            ORDER BY device_id ASC
        ''')
        rows = c.fetchall()
        devices = {r[0]: (json.loads(r[1]), r[2]) for r in rows}
        
        # Get recent critical alerts (Risk > 50)
        c.execute('SELECT device_id, payload, timestamp FROM sensor_logs ORDER BY id DESC LIMIT 100')
        recent = c.fetchall()
        alerts = []
        for r in recent:
            p = json.loads(r[1])
            if p.get('risk_score', 0) > 50:
                alerts.append((r[0], p, r[2]))
                if len(alerts) >= 8:
                    break
        conn.close()
        return devices, alerts
    except Exception as e:
        return {}, []

def draw_tui(stdscr):
    # Setup Colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE) # Inverted for headers
    
    curses.curs_set(0) # Hide cursor
    curses.halfdelay(10) # 1 second timeout for getch(), creates our tick rate

    while True:
        max_y, max_x = stdscr.getmaxyx()
        stdscr.clear()

        # Gather real-time data
        load_avg = get_sys_load()
        mem_usage = get_sys_mem()
        devices, alerts = get_db_data()
        
        # --- 1. HEADER ---
        header_text = f" VERS-TOP (v2.4) | Load: {load_avg} | Mem: {mem_usage} | Time: {datetime.now().strftime('%H:%M:%S')} "
        stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
        stdscr.addstr(0, 0, header_text.ljust(max_x)[:max_x])
        stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)
        
        # --- 2. TABLE COLUMNS ---
        if max_y > 2:
            cols = f"{'NODE ID':<15} | {'RISK':<4} | {'BAT':<4} | {'FIRE':<4} | {'FLD':<4} | {'LIFE':<4} | {'GAS':<4} | {'LAST SEEN':<8}"
            stdscr.attron(curses.A_UNDERLINE)
            stdscr.addstr(2, 0, cols[:max_x])
            stdscr.attroff(curses.A_UNDERLINE)

        # --- 3. DEVICE ROWS ---
        row = 3
        for dev_id, (payload, ts) in devices.items():
            if row >= max_y - 10: # Leave room for alerts at bottom
                break
            
            risk = payload.get('risk_score', 0)
            sensors = payload.get('sensors', {})
            bat = payload.get('battery', 0)
            
            fire = "FIRE" if sensors.get('fire') else "CLR"
            fld = "YES" if sensors.get('flood') else "DRY"
            life = "DET" if sensors.get('life_form') else "CLR"
            gas = str(sensors.get('gas', 0))
            
            # Format timestamp nicely
            time_str = ts.split('T')[1][:8] if 'T' in ts else ts
            
            # Print Base Node ID
            stdscr.addstr(row, 0, f"{dev_id[:15]:<15} | ")
            
            # Print Risk with Color
            risk_color = curses.color_pair(2) if risk > 50 else (curses.color_pair(3) if risk > 0 else curses.color_pair(1))
            stdscr.attron(risk_color)
            stdscr.addstr(row, 18, f"{risk:<4}")
            stdscr.attroff(risk_color)
            stdscr.addstr(row, 22, " | ")
            
            # Print Battery with Color
            bat_color = curses.color_pair(2) if bat < 20 else curses.color_pair(1)
            stdscr.attron(bat_color)
            stdscr.addstr(row, 25, f"{bat:<3}%")
            stdscr.attroff(bat_color)
            stdscr.addstr(row, 29, " | ")
            
            # Print Fire Sensor
            f_color = curses.color_pair(2) if fire == "FIRE" else curses.color_pair(1)
            stdscr.attron(f_color)
            stdscr.addstr(row, 32, f"{fire:<4}")
            stdscr.attroff(f_color)
            stdscr.addstr(row, 36, " | ")
            
            # Print Flood Sensor
            fl_color = curses.color_pair(2) if fld == "YES" else curses.color_pair(1)
            stdscr.attron(fl_color)
            stdscr.addstr(row, 39, f"{fld:<4}")
            stdscr.attroff(fl_color)
            stdscr.addstr(row, 43, " | ")
            
            # Print Life Form Sensor
            l_color = curses.color_pair(2) if life == "DET" else curses.color_pair(1)
            stdscr.attron(l_color)
            stdscr.addstr(row, 46, f"{life:<4}")
            stdscr.attroff(l_color)
            stdscr.addstr(row, 50, " | ")
            
            # Print Gas and Timestamp
            stdscr.addstr(row, 53, f"{gas:<4} | {time_str:<8}")
            row += 1

        # --- 4. CRITICAL ALERTS SECTION ---
        alert_start_row = max(row + 2, max_y - 10)
        if alert_start_row < max_y - 1:
            stdscr.attron(curses.color_pair(5))
            stdscr.addstr(alert_start_row, 0, " RECENT CRITICAL EVENTS (Risk > 50) ".ljust(max_x)[:max_x])
            stdscr.attroff(curses.color_pair(5))
            
            arow = alert_start_row + 1
            for dev_id, p, ts in alerts:
                if arow >= max_y - 1:
                    break
                t_str = ts.split('T')[1][:8] if 'T' in ts else ts
                risk = p.get('risk_score', 0)
                
                # Format triggers
                em = []
                s = p.get('sensors', {})
                if s.get('fire'): em.append('FIRE')
                if s.get('flood'): em.append('FLOOD')
                if s.get('life_form'): em.append('LIFE_FORM')
                if s.get('gas',0) > 200: em.append('GAS')
                
                msg = f"[{t_str}] {dev_id}: Risk {risk} | Triggers: {', '.join(em)}"
                stdscr.attron(curses.color_pair(2))
                stdscr.addstr(arow, 0, msg[:max_x])
                stdscr.attroff(curses.color_pair(2))
                arow += 1
                
        # --- 5. FOOTER ---
        footer = " Press 'q' to quit | Real-time monitoring active "
        stdscr.addstr(max_y - 1, 0, footer[:max_x], curses.color_pair(4) | curses.A_BOLD)

        stdscr.refresh()
        
        # Check for user input, breaks loop if 'q' is pressed
        try:
            c = stdscr.getch()
            if c == ord('q') or c == ord('Q'):
                break
        except curses.error:
            pass

if __name__ == "__main__":
    try:
        curses.wrapper(draw_tui)
    except KeyboardInterrupt:
        pass
    print("Exited VERS-TOP Monitor.")
