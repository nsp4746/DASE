import dearpygui.dearpygui as dpg
import json
import threading
import os
import platform
import ctypes
from dase import utils
from queue import Queue, Empty
from dase.simulation import SimulationSession, MODEL_OPTIONS
from dase.providers.mlx import MLXConfig

"""
GUI for DASE Training Interface using Dear PyGui.
"""
def _decode_unicode(text: str) -> str:
    """
    Convert escape sequences such as '\\u2019' into their actual characters
    so Dear PyGui renders them correctly.
    """
    # Normalize curly quotes/dashes to ASCII so missing glyphs don't render as '?'
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }
    text = "".join(replacements.get(ch, ch) for ch in text)
    # Decode escape sequences only when present to avoid mangling real Unicode chars.
    if "\\u" not in text and "\\x" not in text:
        return text
    try:
        return text.encode("utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return text
    
    
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
    scale = 1.0 # Temp Fix for macOS DPI
    print("macOS detected. Dear PyGui should handle DPI scaling automatically.")

else:
    print("Non-Windows platform detected. Using Native DPI Scaling.")
    scale = 1.0

dpg.create_context()
dpg.configure_app(manual_callback_management=True)
dpg.create_viewport(title='DASE Training Interface', width=800, height=700)
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
        font_paths = [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf"
        ]
    elif system == "Darwin": # macOS
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Menlo.ttc"
        ]
    else:
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
    with dpg.theme() as app_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, (230, 230, 230, 255))
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (24, 24, 27, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, round(6 * scale))
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, round(6 * scale), round(6 * scale))
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, round(8 * scale), round(8 * scale))
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, round(12 * scale))
            dpg.add_theme_style(dpg.mvStyleVar_GrabMinSize, round(12 * scale))
            
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (18, 18, 20, 255))
    dpg.bind_theme(app_theme)

    font_path = _find_system_font()
    
    base_font_size = 18
    scaled_font_size = int(base_font_size * scale)
    print(f"Loading font at {scaled_font_size}px (Base: {base_font_size}px * Scale: {scale})")

    with dpg.font_registry():
        default_font = None
        if font_path:
            try:
                default_font = dpg.add_font(font_path, scaled_font_size)
                # Ensure common punctuation (curly quotes/dashes) render instead of showing '?'.
                try:
                    if hasattr(dpg, "add_font_range_hint"):
                        try:
                            dpg.add_font_range_hint(default_font, dpg.mvFontRangeHint_Default)
                            dpg.add_font_range_hint(default_font, dpg.mvFontRangeHint_Latin)
                        except TypeError:
                            dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
                            dpg.add_font_range_hint(dpg.mvFontRangeHint_Latin)
                    if hasattr(dpg, "add_font_range"):
                        dpg.add_font_range(default_font, 0x2000, 0x206F)  # General Punctuation block
                except Exception as e:
                    print(f"Warning: could not extend font ranges: {e}")
            except Exception as e:
                print(f"Error loading font {font_path}: {e}")
                default_font = None
                
        if default_font is not None:
            dpg.bind_font(default_font)
        else:
            print("Binding default font and using set_global_font_scale as fallback.")
            dpg.set_global_font_scale(scale)

install_theme_and_fonts(scale)

# Every worker captures one session reference and returns through this queue.
active_session = None
active_session_log = None
results = Queue()
busy = False
step = 0


def set_busy(value):
    global busy
    busy = value
    dpg.configure_item("loading_indicator", show=value)
    for tag in ("send_button", "end_button", "save_button", "user_input"):
        dpg.configure_item(tag, enabled=not value)


def start_session_callback():
    global active_session, active_session_log, step
    if busy:
        return
    try:
        company_name = dpg.get_value("company_combo")
        difficulty = dpg.get_value("difficulty_combo")
        reactions = dpg.get_value("reactions_input")
        model_choice = dpg.get_value("model_combo")
        with open(utils.COMPANY_MAP[company_name], encoding="utf-8") as f:
            profile = json.dumps(json.load(f), indent=2)
        session = SimulationSession(model_choice, profile, company_name, difficulty, reactions,
                                    local_model=dpg.get_value("mlx_model_input"))
    except Exception as exc:
        dpg.set_value("setup_error", f"Could not start session: {exc}")
        return
    active_session = session
    active_session_log = session.log
    step = 0
    dpg.set_value("setup_error", "")
    dpg.set_value("user_input", "")
    dpg.configure_item("setup_window", show=False)
    dpg.configure_item("chat_window", show=True)
    dpg.set_primary_window("chat_window", True)
    dpg.delete_item("chat_display", children_only=True)
    dpg.add_text(
        f"Session started for {company_name} using {model_choice}, difficulty {difficulty}, {reactions} reactions.",
        parent="chat_display", color=SYSTEM_COLOR, wrap=wrap_width("chat_display"))
    dpg.add_text("Enter the attack type or scenario you want to simulate.",
                 parent="chat_display", color=SYSTEM_COLOR, wrap=wrap_width("chat_display"))


def send_message_callback():
    global step
    if busy or active_session is None:
        return
    user_input = dpg.get_value("user_input").strip()
    if not user_input:
        return
    session = active_session
    set_busy(True)
    dpg.add_text(f"User: {user_input}", parent="chat_display", color=USER_COLOR,
                 wrap=wrap_width("chat_display"))
    dpg.set_value("user_input", "")
    step += 1
    response_tag = f"model_response_{step}"
    dpg.add_text("DASE: Generating...", parent="chat_display", tag=response_tag,
                 color=MODEL_COLOR, wrap=wrap_width("chat_display"))

    def generate_response():
        try:
            response = session.send(user_input)
            results.put((session, response_tag, response, None))
        except Exception as exc:
            results.put((session, response_tag, None, str(exc)))

    threading.Thread(target=generate_response, daemon=True).start()


def process_results():
    # Called only by the main render loop. No worker calls Dear PyGui.
    while True:
        try:
            session, tag, response, error = results.get_nowait()
        except Empty:
            return
        if session is active_session:
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, f"DASE: {error if error else _decode_unicode(response)}")
            set_busy(False)


def back_to_setup_callback():
    """
    Returns to the setup screen from the chat window.
    """
    if busy:
        return
    dpg.configure_item("chat_window", show=False)
    dpg.configure_item("setup_window", show=True)
    dpg.set_primary_window("setup_window", True)


def save_session_callback():
    """
    Saves the current session log to disk.
    """
    if busy:
        return
    if active_session_log is None:
        dpg.add_text(
            "No active session to save.",
            parent="chat_display",
            color=(255, 99, 71, 255),
            wrap=wrap_width("chat_display")
        )
        return
    try:
        file_path = utils.save_session(active_session_log)
        dpg.add_text(
            f"Session saved to {file_path}",
            parent="chat_display",
            color=SYSTEM_COLOR,
            wrap=wrap_width("chat_display")
        )
    except Exception as e:
        dpg.add_text(
            f"Failed to save session: {e}",
            parent="chat_display",
            color=(255, 99, 71, 255),
            wrap=wrap_width("chat_display")
        )

# --- UI Definition ---

with dpg.window(label="Setup", tag="setup_window", width=800, height=700):
    dpg.add_text("DASE Session Setup")
    dpg.add_spacer(height=10)

    dpg.add_text("Select Company:")
    dpg.add_combo(list(utils.COMPANY_MAP.keys()), default_value="Well Connect", tag="company_combo", width=250)
    dpg.add_spacer(height=10)

    dpg.add_text("Select Model:")
    default_provider = os.getenv("DASE_DEFAULT_PROVIDER", MODEL_OPTIONS[0])
    if default_provider not in MODEL_OPTIONS:
        default_provider = MODEL_OPTIONS[0]
    dpg.add_combo(MODEL_OPTIONS, default_value=default_provider, tag="model_combo", width=250)
    dpg.add_spacer(height=10)

    dpg.add_text("Local MLX model (must be available to your localhost server):")
    dpg.add_input_text(default_value=os.getenv("MLX_MODEL", MLXConfig.model),
                       tag="mlx_model_input", width=500)
    dpg.add_spacer(height=10)

    dpg.add_text("Select Difficulty:")
    dpg.add_combo(["low", "medium", "high"], default_value="low", tag="difficulty_combo", width=250)
    dpg.add_spacer(height=10)

    dpg.add_text("Select Number of Reactions:")
    dpg.add_input_int(default_value=3, tag="reactions_input", width=250, min_value=1, max_value=10)
    dpg.add_spacer(height=20)

    dpg.add_button(label="Start Session", callback=start_session_callback)
    dpg.add_text("", tag="setup_error", color=(255, 99, 71, 255), wrap=700)

with dpg.window(label="Chat", tag="chat_window", show=False, width=800, height=700):
    with dpg.child_window(tag="chat_display", height=-70):
        pass 

    with dpg.group(horizontal=True):
        dpg.add_input_text(
            tag="user_input",
            hint="Type your message here...",
            on_enter=True,
            callback=send_message_callback,
            width=-220
        )
        dpg.add_button(label="Send", tag="send_button", callback=send_message_callback, width=60)
        dpg.add_button(label="End", tag="end_button", callback=back_to_setup_callback, width=60)
        with dpg.group(horizontal=True):
            dpg.add_loading_indicator(tag="loading_indicator", show=False, style=1, radius=1.5)

    dpg.add_spacer(height=6)
    dpg.add_button(label="Save Session", tag="save_button", callback=save_session_callback, width=140)

dpg.set_primary_window("setup_window", True)
dpg.show_viewport()
while dpg.is_dearpygui_running():
    dpg.run_callbacks(dpg.get_callback_queue())
    process_results()
    dpg.render_dearpygui_frame()
dpg.destroy_context()
