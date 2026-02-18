"""Performance utilities for parallel loading and optimization."""

import streamlit as st
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Tuple, Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


def load_data_parallel(tasks: Optional[Union[List[Tuple[str, Callable]], List[Tuple[str, Callable, tuple]]]] = None, *args_tasks) -> Dict[str, Any]:
    """
    Load multiple data items in parallel using thread pool.
    
    Usage:
        # Option 1: Pass list of tuples with (name, callable) - args passed as *args to callable
        result = load_data_parallel([
            ("project_info", fetch_project_func),
            ("sprint_info", fetch_sprint_func),
        ])
        
        # Option 2: Pass individual tuples (legacy format)
        result = load_data_parallel(
            ("name1", callable1, (arg1, arg2)),
            ("name2", callable2, (arg1,))
        )
        
    Args:
        tasks: List of tuples (name, callable) where callable takes no args, or
               List of tuples (name, callable, args_tuple) where callable takes args
            
    Returns:
        Dictionary with keys from task names and values as results
    """
    results: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    
    # Handle both list and variable args formats
    task_list: List[Any] = []
    if tasks is None:
        task_list = list(args_tasks)
    elif isinstance(tasks, list):
        # Normalize list format to ensure consistent structure
        task_list = [t if len(t) == 3 else (t[0], t[1], ()) for t in tasks]
    else:
        # Convert single task to list
        task_list = [tasks] + list(args_tasks)
    
    with ThreadPoolExecutor(max_workers=min(3, len(task_list))) as executor:
        # Submit all tasks, handling both formats
        future_to_name: Dict[Any, str] = {}
        for task in task_list:
            if len(task) == 3:
                name, callable_func, args = task
                future = executor.submit(callable_func, *args)
            else:
                name, callable_func = task
                future = executor.submit(callable_func)
            future_to_name[future] = name
        
        # Collect results as they complete
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result()
                logger.info(f"✓ Loaded {name}")
            except Exception as e:
                errors[name] = str(e)
                logger.error(f"✗ Error loading {name}: {str(e)}")
                results[name] = None
    
    return results


def init_session_cache(cache_key: str, load_func: Callable, *args, **kwargs) -> Any:
    """
    Initialize session state cache for a value.
    Only loads if not already cached in session.
    
    Usage:
        data = init_session_cache(
            'dashboard_data',
            fetch_and_process_data,
            jira, project_key
        )
    
    Args:
        cache_key: Session state key to store value
        load_func: Function to call if cache miss
        *args: Arguments to pass to load_func
        **kwargs: Keyword arguments to pass to load_func
        
    Returns:
        Cached or newly loaded data
    """
    if cache_key not in st.session_state:
        st.session_state[cache_key] = load_func(*args, **kwargs)
    
    return st.session_state[cache_key]


def clear_session_cache(pattern: Optional[str] = None) -> None:
    """
    Clear session cache by key pattern or all.
    
    Usage:
        clear_session_cache()  # Clear all
        clear_session_cache("dashboard")  # Clear matching keys
    
    Args:
        pattern: Optional pattern to match keys (case-insensitive)
    """
    if pattern is None:
        st.session_state.clear()
        logger.info("Cleared all session cache")
    else:
        pattern_lower = pattern.lower()
        keys_to_clear = [k for k in st.session_state.keys() if isinstance(k, str) and pattern_lower in k.lower()]
        for key in keys_to_clear:
            del st.session_state[key]
        logger.info(f"Cleared {len(keys_to_clear)} cache keys matching '{pattern}'")


def show_loading_animation(message: str = "Loading...") -> None:
    """
    Display professional loading animation.
    
    Usage:
        show_loading_animation("Fetching data from Jira...")
    """
    st.markdown(f"""
        <div style="text-align: center; padding: 20px;">
            <p style="font-size: 18px; color: #0052CC; margin-bottom: 10px;">
                🔄 {message}
            </p>
            <div style="display: flex; justify-content: center; gap: 8px;">
                <span style="animation: pulse 1s infinite;">●</span>
                <span style="animation: pulse 1s 0.2s infinite;">●</span>
                <span style="animation: pulse 1s 0.4s infinite;">●</span>
            </div>
        </div>
        <style>
            @keyframes pulse {{
                0%, 100% {{ opacity: 0.3; }}
                50% {{ opacity: 1; }}
            }}
        </style>
    """, unsafe_allow_html=True)


def get_last_update_time() -> str:
    """Get formatted last update time for display."""
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")


def display_update_timestamp() -> None:
    """Display last update timestamp in the UI."""
    st.caption(f"⏰ Last updated: {get_last_update_time()}")
