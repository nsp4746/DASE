import dearpygui.dearpygui as dpg
import gemini
import json
import threading
import os
import platform
import ctypes


scale_factor = 1.0
# DPI Context Aware
if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # SYSTEM_AWARE
        scale_raw = ctypes.windll.shcore.GetScaleFactorForDevice(0)

        if scale_raw > 0:
            scale = scale_raw / 100.0
            print(f"Detected Windows scaling factor: {scale:.2f}")
        else:
            print("Warning: Could not get DPI scale from Windows. Defaulting to 1.0.")
            scale = 1.0
    except Exception as e:
        print(f"Warning: Could not set DPI awareness. {e}")
elif platform.system() == "Darwin":
    print("macOS detected. Dear PyGui should handle DPI scaling automatically.")

else:
    print("Non-Windows platform detected. Using Native DPI Scaling.")

dpg.create_context()
dpg.create_viewport(title='DASE Gemini Interface', width=800, height=700)
dpg.setup_dearpygui()

# --- Visual Constants / Helpers ---
WRAP_PAD = 20
USER_COLOR = (82, 156, 255, 255)
MODEL_COLOR = (230, 230, 230, 255)
SYSTEM_COLOR = (200, 200, 200, 255)


def _find_system_font() -> str | None:
    """
    Tries to find a good-quality, cross-platform system font.
    """
    system = platform.system()
    
    if system == "Windows":
        # Segoe UI is the standard. Arial is a safe fallback.
        font_paths = [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf"
        ]
    elif system == "Darwin": # macOS
        # Helvetica is standard on macOS.
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Menlo.ttc"
        ]
    else: # Linux
        # DejaVu and Liberation are common and high-quality.
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf" # Other common path
        ]
        
    for path in font_paths:
        if os.path.exists(path):
            print(f"Found system font: {path}")
            return path
            
    print("Warning: Could not find a recommended system font. Using DPG default.")
    return None


def wrap_width(tag: str, pad: int = WRAP_PAD) -> int:
    # (Your function is fine, no changes needed)
    w = dpg.get_item_width(tag)
    try:
        w_int = int(w)
    except Exception:
        w_int = 0
    return max(0, w_int - pad)

# def wrap_width(tag: str, pad: int = WRAP_PAD) -> int:
#     """Return a safe wrap width for a Dear PyGui item.
#     Avoid negatives if width is unset or not yet measured.
#     """
#     w = dpg.get_item_width(tag)
#     try:
#         w_int = int(w)
#     except Exception:
#         w_int = 0
#     return max(0, w_int - pad)

def install_theme_and_fonts(scale: float):
    """Install a theme and font, scaled for the detected DPI.
    
    Args:
        scale (float): The detected DPI scale factor (e.g., 1.0, 1.5).
    """
    # Simple dark theme with comfortable, SCALED spacing
    with dpg.theme() as app_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, (230, 230, 230, 255))
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (24, 24, 27, 255))
            # Scale all style variables
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, round(6 * scale))
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, round(6 * scale), round(6 * scale))
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, round(8 * scale), round(8 * scale))
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, round(12 * scale))
            dpg.add_theme_style(dpg.mvStyleVar_GrabMinSize, round(12 * scale))
            
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (18, 18, 20, 255))
    dpg.bind_theme(app_theme)

    # Try to find and load a high-quality system font
    font_path = _find_system_font()
    
    # Scale the font size. This gives MUCH sharper text than set_global_font_scale()
    base_font_size = 18
    scaled_font_size = int(base_font_size * scale)
    print(f"Loading font at {scaled_font_size}px (Base: {base_font_size}px * Scale: {scale})")

    with dpg.font_registry():
        default_font = None
        if font_path:
            try:
                # Add the font at the correctly scaled size
                default_font = dpg.add_font(font_path, scaled_font_size)
            except Exception as e:
                print(f"Error loading font {font_path}: {e}")
                default_font = None
                
        if default_font is not None:
            dpg.bind_font(default_font)
        else:
            # Fallback: Use default font and scale it (will be blurrier)
            print("Binding default font and using set_global_font_scale as fallback.")
            default_font = dpg.add_font(tag="default_font") # Get default
            dpg.bind_font(default_font)
            dpg.set_global_font_scale(scale) # Blurry, but correctly-sized

# def install_theme_and_fonts():
    """Install a light readability theme and try to bind a clean UI font.
    Falls back gracefully if the font path is unavailable.
    """
    # Simple dark theme with comfortable spacing
    with dpg.theme() as app_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, (230, 230, 230, 255))
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (24, 24, 27, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 6, 6)
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (18, 18, 20, 255))
    dpg.bind_theme(app_theme)

    # Try to use Segoe UI on Windows for improved readability
    font_path = r"C:\\Windows\\Fonts\\segoeui.ttf"
    with dpg.font_registry():
        default_font = None
        if os.path.exists(font_path):
            try:
                default_font = dpg.add_font(font_path, 18)
            except Exception:
                default_font = None
        if default_font is not None:
            dpg.bind_font(default_font)
    # Slight global scale for readability (kept gentle)
    dpg.set_global_font_scale(1.05)
    
# install theme/fonts before building any UI
install_theme_and_fonts(scale)

# --- Global State ---
company_profile_str = ""
difficulty = "low"
reactions = 1
step = 0

company_map = {
    "Well Connect": "well_connect.json",
    "AeroPay": "aeropay.json",
    "MetroGrid Manufacturing": "metrogrid.json"
}

# --- Callbacks ---
def start_session_callback():
    """
    Loads company profile, sets up chat parameters, and switches to the chat window.
    """
    global company_profile_str, difficulty, reactions, step

    # Get values from setup window
    company_name = dpg.get_value("company_combo")
    difficulty = dpg.get_value("difficulty_combo")
    reactions = dpg.get_value("reactions_input")

    company_file = company_map.get(company_name)
    if not company_file:
        print("Invalid company selection.")
        return

    with open(company_file, 'r') as f:
        company_profile = json.load(f)
    company_profile_str = json.dumps(company_profile, indent=2)

    # Reset conversation state
    gemini.conversation_history.clear()
    step = 0

    # Switch views
    dpg.configure_item("setup_window", show=False)
    dpg.configure_item("chat_window", show=True)
    dpg.set_primary_window("chat_window", True)

    # Clear and update chat display
    dpg.delete_item("chat_display", children_only=True)
    dpg.add_text(
        f"Session started for {company_name} with difficulty '{difficulty}' and {reactions} reaction(s).",
        parent="chat_display",
        color=SYSTEM_COLOR,
        wrap=wrap_width("chat_display")
    )
    dpg.add_text(
        "Please enter your scenario description below.",
        parent="chat_display",
        color=SYSTEM_COLOR,
        wrap=wrap_width("chat_display")
    )


def send_message_callback():
    """
    Sends user input to the Gemini model and displays the streaming response.
    """
    global step
    user_input = dpg.get_value("user_input")
    if not user_input:
        return

    # Add user message to chat display
    dpg.add_text(
        f"User: {user_input}",
        parent="chat_display",
        color=USER_COLOR,
        wrap=wrap_width("chat_display")
    )
    dpg.set_value("user_input", "") # Clear input field

    # Prepare the prompt (first message includes context)
    if step == 0:
        company_name = dpg.get_value("company_combo")
        full_prompt = (
            f"{user_input}\nThe user desires this level of technical difficulty: {difficulty} "
            f"and this number of reactions {reactions}. The company to perform the exercise on is {company_name}."
        )
    else:
        full_prompt = user_input

    # Increment step for every message to ensure unique tags
    step += 1

    # Generate a unique tag for the model's response text widget
    model_response_tag = f"model_response_{step}"

    # Add model response placeholder
    dpg.add_text(
        "DASE: ",
        parent="chat_display",
        tag=model_response_tag,
        color=MODEL_COLOR,
        wrap=wrap_width("chat_display")
    )

    # Run model generation in a separate thread to keep the GUI responsive
    def stream_response():
        full_response_text = "DASE: "
        for chunk in gemini.generate(full_prompt, company_profile_str):
            full_response_text += chunk
            # Check if the item still exists before trying to set its value
            if dpg.does_item_exist(model_response_tag):
                dpg.set_value(model_response_tag, full_response_text)

    threading.Thread(target=stream_response, daemon=True).start()

def back_to_setup_callback():
    """
    Returns to the setup screen from the chat window.
    """
    dpg.configure_item("chat_window", show=False)
    dpg.configure_item("setup_window", show=True)
    dpg.set_primary_window("setup_window", True)

# --- UI Definition ---

with dpg.window(label="Setup", tag="setup_window", width=800, height=700):
    dpg.add_text("DASE Gemini Interface Setup")
    dpg.add_spacer(height=10)

    dpg.add_text("Select Company:")
    dpg.add_combo(list(company_map.keys()), default_value="Well Connect", tag="company_combo", width=250)
    dpg.add_spacer(height=10)

    dpg.add_text("Select Difficulty:")
    dpg.add_combo(["low", "medium", "high"], default_value="low", tag="difficulty_combo", width=250)
    dpg.add_spacer(height=10)

    dpg.add_text("Select Number of Reactions:")
    dpg.add_input_int(default_value=3, tag="reactions_input", width=250, min_value=1, max_value=10)
    dpg.add_spacer(height=20)

    dpg.add_button(label="Start Session", callback=start_session_callback)

with dpg.window(label="Chat", tag="chat_window", show=False, width=800, height=700):
    with dpg.child_window(tag="chat_display", height=-70):
        pass # Chat messages will be added here dynamically

    with dpg.group(horizontal=True):
        dpg.add_input_text(
            tag="user_input",
            hint="Type your message here...",
            on_enter=True,
            callback=send_message_callback,
            width=-120 # Fill width leaving space for buttons
        )
        dpg.add_button(label="Send", callback=send_message_callback, width=50)
        dpg.add_button(label="End", callback=back_to_setup_callback, width=50)

dpg.set_primary_window("setup_window", True)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
