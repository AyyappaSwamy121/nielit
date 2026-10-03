from django.contrib import admin
from .models import (
    Country, State, District, Religion, MaritalStatus, ExServiceStatus, 
    Community, Occupation, Qualification, YearOfStudy, Program, ApplicationStatus
)

class MasterBaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'is_active', 'created_at', 'updated_at')
    list_editable = ('display_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('display_order', 'id')
    actions = ['make_active', 'make_inactive']

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('import-excel/', self.admin_site.admin_view(self.import_excel_view), name=f'{self.model._meta.model_name}_import_excel'),
        ]
        return custom_urls + urls

    def import_excel_view(self, request):
        from django.shortcuts import render, redirect
        from django.contrib import messages
        import openpyxl

        if request.method == "POST":
            excel_file = request.FILES.get("excel_file")
            if not excel_file:
                messages.error(request, "No file uploaded.")
                return redirect("..")
            
            try:
                wb = openpyxl.load_workbook(excel_file, data_only=True)
                ws = wb.active
                
                # Assume columns: Country | State | District
                # First row is header
                rows = list(ws.iter_rows(values_only=True))
                if len(rows) <= 1:
                    messages.error(request, "Excel file is empty or only contains headers.")
                    return redirect("..")
                
                headers = [str(h).strip().lower() for h in rows[0]]
                country_idx = headers.index('country') if 'country' in headers else 0
                state_idx = headers.index('state') if 'state' in headers else 1
                district_idx = headers.index('district') if 'district' in headers else 2
                
                countries_added = 0
                states_added = 0
                districts_added = 0
                
                for row in rows[1:]:
                    if not row[country_idx]:
                        continue
                    
                    c_name = str(row[country_idx]).strip()
                    s_name = str(row[state_idx]).strip() if row[state_idx] else None
                    d_name = str(row[district_idx]).strip() if row[district_idx] else None
                    
                    country_obj, c_created = Country.objects.get_or_create(
                        name__iexact=c_name,
                        defaults={'name': c_name, 'code': c_name[:3].upper()}
                    )
                    if c_created: countries_added += 1
                    
                    state_obj = None
                    if s_name:
                        state_obj, s_created = State.objects.get_or_create(
                            name__iexact=s_name, country=country_obj,
                            defaults={'name': s_name, 'code': s_name[:3].upper(), 'country': country_obj}
                        )
                        if s_created: states_added += 1
                        
                    if state_obj and d_name:
                        _, d_created = District.objects.get_or_create(
                            name__iexact=d_name, state=state_obj,
                            defaults={'name': d_name, 'code': d_name[:3].upper(), 'state': state_obj}
                        )
                        if d_created: districts_added += 1
                        
                messages.success(request, f"Import successful! Added {countries_added} Countries, {states_added} States, and {districts_added} Districts.")
                return redirect("..")
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                return redirect("..")

        return render(request, "admin/masterdata/import_master_data.html", {})

    def changelist_view(self, request, extra_context=None):
        if self.model in [Country, State, District]:
            extra_context = extra_context or {}
            extra_context['show_import_button'] = True
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description="Mark selected items as Active")
    def make_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Mark selected items as Inactive")
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(Country)
class CountryAdmin(MasterBaseAdmin):
    list_display = ('name', 'code', 'display_order', 'is_active')
    search_fields = ('name', 'code')

@admin.register(State)
class StateAdmin(MasterBaseAdmin):
    list_display = ('name', 'code', 'country', 'display_order', 'is_active')
    list_filter = ('country', 'is_active')
    search_fields = ('name', 'code')

@admin.register(District)
class DistrictAdmin(MasterBaseAdmin):
    list_display = ('name', 'code', 'state', 'display_order', 'is_active')
    list_filter = ('state__country', 'state', 'is_active')
    search_fields = ('name', 'code')

@admin.register(Religion)
class ReligionAdmin(MasterBaseAdmin):
    pass

@admin.register(MaritalStatus)
class MaritalStatusAdmin(MasterBaseAdmin):
    pass

@admin.register(ExServiceStatus)
class ExServiceStatusAdmin(MasterBaseAdmin):
    pass

@admin.register(Community)
class CommunityAdmin(MasterBaseAdmin):
    list_display = ('name', 'short_name', 'display_order', 'is_active')

@admin.register(Occupation)
class OccupationAdmin(MasterBaseAdmin):
    pass

@admin.register(Qualification)
class QualificationAdmin(MasterBaseAdmin):
    list_display = ('name', 'code', 'display_order', 'is_active')

@admin.register(YearOfStudy)
class YearOfStudyAdmin(MasterBaseAdmin):
    pass

@admin.register(Program)
class ProgramAdmin(MasterBaseAdmin):
    list_display = ('name', 'duration', 'display_order', 'is_active')

@admin.register(ApplicationStatus)
class ApplicationStatusAdmin(MasterBaseAdmin):
    list_display = ('name', 'code', 'display_order', 'is_active')
    search_fields = ('name', 'code')
