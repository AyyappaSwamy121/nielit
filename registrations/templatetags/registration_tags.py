from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Return mapping[key], used to look up form_data values by dynamic field name."""
    try:
        return mapping.get(key, '') if hasattr(mapping, 'get') else mapping[key]
    except (TypeError, KeyError, IndexError):
        return ''


@register.simple_tag
def facet_counts(changelist, spec):
    """Compute Django Admin facet counts for one filter spec (only when enabled)."""
    if not getattr(changelist, 'add_facets', False):
        return {}
    try:
        return spec.get_facet_queryset(changelist)
    except Exception:
        return {}


@register.filter
def facet_count(counts, index):
    """Return the facet count for the lookup_choices position at ``index``."""
    try:
        return counts.get('%s__c' % index)
    except (AttributeError, TypeError):
        return None
