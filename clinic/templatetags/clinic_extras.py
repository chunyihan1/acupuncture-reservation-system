from django import template

register = template.Library()


@register.filter
def mask_phone(value):
    if not value:
        return "—"
    text = str(value)
    if len(text) < 7:
        return text[:2] + "****"
    return f"{text[:3]}****{text[-4:]}"


@register.filter
def mask_name(value):
    if not value:
        return "—"
    text = str(value)
    if len(text) <= 1:
        return text + "*"
    return text[0] + "*" * (len(text) - 1)


@register.filter
def short_status(value):
    return value or "—"


@register.filter
def elided_pages(paginator, number):
    try:
        return paginator.get_elided_page_range(number, on_each_side=1, on_ends=1)
    except AttributeError:
        return paginator.page_range
