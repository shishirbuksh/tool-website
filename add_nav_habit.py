import os
import re

base_path = r"d:\fr\ruff1\tool\templates\base.html"

with open(base_path, 'r', encoding='utf-8') as f:
    content = f.read()

habit_tracker_desktop = '<li><a class="dropdown-item" href="/tool/habit-tracker"><i class="bi bi-calendar-check"></i><div>Habit Tracker<span class="desc">Track daily routines</span></div></a></li>'
habit_tracker_mobile = '<a href="/tool/habit-tracker" class="list-group-item list-group-item-action bg-transparent border-0 px-2 py-1 rounded-3 text-theme sidebar-item">Habit Tracker</a>'

# Insert into desktop navbar (under Productivity)
# Look for: <a class="dropdown-item" href="/tool/note-organizer"><i class="bi bi-book"></i><div>Note Organizer<span class="desc">Write and save notes</span></div></a></li>
pattern_desk = r'(<li><a class="dropdown-item" href="/tool/note-organizer">.*?</a></li>)'
content = re.sub(pattern_desk, r'\1\n                                    ' + habit_tracker_desktop, content)

# Insert into mobile sidebar (under Productivity)
# Look for: <a href="/tool/time-tracker" class="list-group-item list-group-item-action bg-transparent border-0 px-2 py-1 rounded-3 text-theme sidebar-item">Time Tracker</a>
pattern_mob = r'(<a href="/tool/time-tracker" class="list-group-item list-group-item-action bg-transparent border-0 px-2 py-1 rounded-3 text-theme sidebar-item">Time Tracker</a>)'
content = re.sub(pattern_mob, r'\1\n                                ' + habit_tracker_mobile, content)

with open(base_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Added habit tracker to base.html navs")
