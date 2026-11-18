from django import template

from healthcare.subscription_display import (
    annual_price_fcfa,
    medplaque_is_addon,
    plan_structures,
    plan_target,
    plan_theme_slug,
)

register = template.Library()


@register.filter
def sub_plan_theme(plan):
    return plan_theme_slug(plan)


@register.filter
def sub_plan_target(plan):
    return plan_target(plan)


@register.filter
def sub_plan_structures(plan):
    return plan_structures(plan)


@register.filter
def sub_annual_price(monthly):
    return annual_price_fcfa(monthly)


@register.filter
def sub_feature_included(plan_included, feature_code):
    """Usage: {{ plan_included|sub_feature_included:feature.code }} avec plan_included = dict[plan_pk]."""
    if isinstance(plan_included, set):
        return feature_code in plan_included
    return False


@register.simple_tag
def sub_medplaque_addon(plan, plan_included_map):
    codes = plan_included_map.get(plan.pk, set())
    return medplaque_is_addon(plan, codes)


@register.filter
def sub_get_included(plan_included_map, plan_pk):
    return plan_included_map.get(plan_pk, set())
