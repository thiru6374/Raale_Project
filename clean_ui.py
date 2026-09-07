import os
import re

EMOJIS = r'[☀️🖥️🗺️📋🕹️📉⚖️🧪🔍⚙️🏆🧠🔐📡🌐🗂️💥🏥📄👥🚀🛡️📍🚨📱✅📅🌡️⚠️📊🏙️🧪📝🧠🎯🥇🧊✔️❌]'

ICONS = {
    "dashboard.py": ":material/monitoring:",
    "main.py": ":material/dashboard:",
    "risk_map.py": ":material/map:",
    "outreach_planner.py": ":material/assignment:",
    "scenario_simulation.py": ":material/science:",
    "baseline.py": ":material/stacked_bar_chart:",
    "decision_center.py": ":material/psychology:",
    "decision_explainability.py": ":material/search_insights:",
    "fairness_analysis.py": ":material/balance:",
    "experiment_evaluation.py": ":material/biotech:",
    "failure_analysis.py": ":material/troubleshoot:",
    "evidence_report.py": ":material/article:",
    "stakeholder_validation.py": ":material/groups:",
    "override_audit.py": ":material/history:",
    "operations_control_center.py": ":material/settings_applications:",
    "final_decision_center.py": ":material/verified:",
    "system_monitoring.py": ":material/speed:",
    "system_health.py": ":material/health_and_safety:",
    "release_readiness.py": ":material/rocket_launch:",
    "security_dashboard.py": ":material/security:",
    "data_sources.py": ":material/database:",
    "data_governance.py": ":material/policy:",
}

def clean_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # 1. Remove all Emojis
    content = re.sub(EMOJIS, "", content)
    
    # 2. Remove Phase references
    content = re.sub(r'Phase\s+\d+\s*[:-]?\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\s*\(Phase\s+\d+\)', '', content, flags=re.IGNORECASE)
    
    # 3. Handle page_icon="xxx" in st.set_page_config
    content = re.sub(r',\s*page_icon="[^"]+"', '', content)
    
    # 4. Replace st.title(...) with page_header(...)
    filename = os.path.basename(filepath)
    icon = ICONS.get(filename)
    
    def title_repl(match):
        title_text = match.group(1).strip()
        if icon:
            return f'page_header({title_text}, subtitle=None, icon="{icon}")'
        return f'page_header({title_text})'
        
    content = re.sub(r'st\.title\((".*?")\)', title_repl, content)
    
    # 5. Inject icon into existing page_header calls if missing
    def header_repl(match):
        title_text = match.group(1)
        sub_text = match.group(2)
        if icon and "icon=" not in match.group(0):
            return f'page_header({title_text}, {sub_text}, icon="{icon}")'
        return match.group(0)
    
    content = re.sub(r'page_header\(([^,]+),\s*([^)]+)\)', header_repl, content)
    
    if content != original_content:
        # Check if we need to import page_header
        if 'page_header' in content and 'page_header' not in original_content:
            if 'from app.components.layout import' in content:
                content = re.sub(r'(from app\.components\.layout import .*?)(?=\n)', r'\1, page_header', content)
            else:
                content = "from app.components.layout import page_header\n" + content

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk("app"):
    for file in files:
        if file.endswith(".py") and file not in ["layout.py", "sidebar.py"]:
            clean_file(os.path.join(root, file))

for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".py"):
            clean_file(os.path.join(root, file))

print("Cleanup script completed.")
