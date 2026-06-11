import os
import re

base_path = r"d:\fr\ruff1\tool\templates\index.html"

with open(base_path, 'r', encoding='utf-8') as f:
    content = f.read()

habit_tracker_card = """
            <div class="col-md-6 col-lg-4">
                <a href="/tool/habit-tracker" class="glass-card tool-card d-block text-decoration-none">
                    <div class="d-flex align-items-center gap-3 mb-3">
                        <div class="tool-icon-wrapper" style="background: rgba(139, 92, 246, 0.1); color: #8b5cf6;">
                            <i class="bi bi-calendar-check fs-4"></i>
                        </div>
                        <h3 class="tool-name">Habit Tracker</h3>
                    </div>
                    <p class="tool-desc">Track daily routines and build positive habits with streaks.</p>
                </a>
            </div>"""

# Insert into Productivity section
# Look for: <div id="productivity" class="category-section"> ... <div class="row g-4">
pattern = r'(<div id="productivity" class="category-section">.*?<div class="row g-4">)'
content = re.sub(pattern, r'\1\n' + habit_tracker_card, content, flags=re.DOTALL)

with open(base_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Added habit tracker to index.html")
