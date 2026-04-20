"""Helper script to show how the Streamlit UI would be started later.

This does not launch Streamlit automatically.
It only prints the command to keep the MVP safe and simple.
"""

from __future__ import annotations


def main() -> None:
    """Print the future Streamlit run command."""
    print("Run the future UI with:")
    print("streamlit run app/ui/streamlit_app.py")


if __name__ == "__main__":
    main()
