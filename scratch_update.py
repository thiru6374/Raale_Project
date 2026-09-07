import os
import glob

PAGES_DIR = r"d:\coe project\neighbourhood-heat-risk-planner\app\pages"
ALREADY_DONE = ["risk_map.py", "outreach_planner.py", "fairness_analysis.py", "override_audit.py"]

files = glob.glob(os.path.join(PAGES_DIR, "*.py"))

for f in files:
    basename = os.path.basename(f)
    if basename in ALREADY_DONE or basename == "__init__.py":
        continue
        
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
        
    if "from app.components.layout import apply_global_styles" in content:
        continue
        
    lines = content.split('\n')
    new_lines = []
    
    injected_imports = False
    injected_calls = False
    
    for line in lines:
        new_lines.append(line)
        
        # Inject imports right after `import streamlit as st`
        if not injected_imports and line.strip() == "import streamlit as st":
            new_lines.append("from app.components.layout import apply_global_styles")
            new_lines.append("from app.components.sidebar import render_sidebar")
            injected_imports = True
            
        # Inject calls right after `st.set_page_config` or `st.title` if config not present
        if not injected_calls and ("st.set_page_config" in line or (not "st.set_page_config" in content and "st.title(" in line)):
            # wait, if it's st.title, we want to inject BEFORE st.title
            pass

    # A better way is to just find `import streamlit as st` and inject imports.
    # Then find `st.set_page_config(...)` or `st.title(...)` and inject the calls right after set_page_config, or BEFORE st.title.
    
    # Let's rebuild properly
    new_lines2 = []
    found_st = False
    for line in lines:
        if line.strip() == "import streamlit as st" and not found_st:
            new_lines2.append(line)
            new_lines2.append("from app.components.layout import apply_global_styles")
            new_lines2.append("from app.components.sidebar import render_sidebar")
            found_st = True
        else:
            new_lines2.append(line)
            
    content2 = "\n".join(new_lines2)
    
    # Now find where to insert the calls
    if "st.set_page_config(" in content2:
        # It spans multiple lines maybe?
        # Let's just insert it after the closing parenthesis of set_page_config
        # This is tricky with regex. 
        pass
        
    # Easiest way: just replace `import streamlit as st` with 
    # import streamlit as st
    # from app.components.layout import apply_global_styles
    # from app.components.sidebar import render_sidebar
    
    # and replace `AppState.initialize_application()` with:
    # apply_global_styles()
    # render_sidebar()
    # AppState.initialize_application()
    
    with open(f, 'w', encoding='utf-8') as file:
        content_mod = content.replace("import streamlit as st", 
            "import streamlit as st\nfrom app.components.layout import apply_global_styles\nfrom app.components.sidebar import render_sidebar")
        
        content_mod = content_mod.replace("AppState.initialize_application()", 
            "apply_global_styles()\nrender_sidebar()\n\nAppState.initialize_application()")
            
        file.write(content_mod)

print("Batch update complete.")
