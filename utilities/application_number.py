from django.utils import timezone
from registrations.models import StudentApplication
from django.db import transaction


def generate_application_number():
    """
    Generates a unique application number automatically.

    Example:
    CSC202600001
    """
    year = timezone.now().year
    prefix = f"CSC{year}"

    with transaction.atomic():
        # Retrieve existing application numbers for this prefix.
        # We cannot rely on ordering by ID because drafts may be
        # submitted out of order.
        existing_numbers = (
            StudentApplication.objects
            .select_for_update()
            .filter(application_number__startswith=prefix)
            .values_list("application_number", flat=True)
        )

        max_seq = 0

        for num in existing_numbers:
            suffix = num[len(prefix):]

            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))

        seq = max_seq + 1
        candidate = f"{prefix}{seq:05d}"

        # Ensure the candidate does not already exist.
        while StudentApplication.objects.filter(
            application_number=candidate
        ).exists():
            seq += 1
            candidate = f"{prefix}{seq:05d}"

        return candidate