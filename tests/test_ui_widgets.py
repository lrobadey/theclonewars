from clone_wars.ui.widgets import AnimatedCollapsible


def test_animated_collapsible_uses_textual_hook_names() -> None:
    assert hasattr(AnimatedCollapsible, "on_mount")
    assert hasattr(AnimatedCollapsible, "watch_collapsed")
    assert hasattr(AnimatedCollapsible, "watch_title")

    assert "_on_mount" not in AnimatedCollapsible.__dict__
    assert "_watch_collapsed" not in AnimatedCollapsible.__dict__
    assert "_watch_title" not in AnimatedCollapsible.__dict__
