import sys

with open('registrations/admin.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.startswith('    def validation_status'):
        skip = True
        
        # Insert properly indented new method
        new_lines.append('    def validation_status(self, obj):\n')
        new_lines.append('        dt = obj.doc_type.lower().replace(" ", "_")\n')
        new_lines.append('        canon_dt = None\n')
        new_lines.append('        if "passport" in dt: canon_dt = "passport_photo"\n')
        new_lines.append('        elif "signature" in dt: canon_dt = "signature"\n')
        new_lines.append('        elif "thumb" in dt: canon_dt = "left_thumb"\n')
        new_lines.append('        \n')
        new_lines.append('        if not canon_dt:\n')
        new_lines.append('            return "-"\n')
        new_lines.append('            \n')
        new_lines.append('        errors = []\n')
        new_lines.append('        \n')
        new_lines.append('        # 1. Format\n')
        new_lines.append('        if not obj.mime_type or obj.mime_type not in ["image/jpeg", "image/jpg"]:\n')
        new_lines.append('            errors.append(f"Format: FAIL - {obj.mime_type}; expected image/jpeg")\n')
        new_lines.append('        else:\n')
        new_lines.append('            errors.append(f"Format: PASS - {obj.mime_type}")\n')
        new_lines.append('            \n')
        new_lines.append('        # 2. Size\n')
        new_lines.append('        kb = obj.optimized_size_kb or obj.original_size_kb or 0\n')
        new_lines.append('        if canon_dt == "passport_photo":\n')
        new_lines.append('            if kb < 5 or kb > 50: errors.append(f"Size: FAIL - {kb} KB (required 5-50 KB)")\n')
        new_lines.append('            else: errors.append(f"Size: PASS - {kb} KB (required 5-50 KB)")\n')
        new_lines.append('        else:\n')
        new_lines.append('            if kb < 5 or kb > 20: errors.append(f"Size: FAIL - {kb} KB (required 5-20 KB)")\n')
        new_lines.append('            else: errors.append(f"Size: PASS - {kb} KB (required 5-20 KB)")\n')
        new_lines.append('            \n')
        new_lines.append('        # 3. Dimensions\n')
        new_lines.append('        w, h = obj.image_width or 0, obj.image_height or 0\n')
        new_lines.append('        if canon_dt == "passport_photo":\n')
        new_lines.append('            if w != 132 or h != 170: errors.append(f"Dimensions: FAIL - {w}x{h} (required 132x170)")\n')
        new_lines.append('            else: errors.append(f"Dimensions: PASS - {w}x{h}")\n')
        new_lines.append('        else:\n')
        new_lines.append('            if w != 170 or h != 132: errors.append(f"Dimensions: FAIL - {w}x{h} (required 170x132)")\n')
        new_lines.append('            else: errors.append(f"Dimensions: PASS - {w}x{h}")\n')
        new_lines.append('            \n')
        new_lines.append('        # 4. DPI\n')
        new_lines.append('        dpi_val = obj.actual_dpi\n')
        new_lines.append('        if not dpi_val:\n')
        new_lines.append('            errors.append("DPI: FAIL - No DPI metadata")\n')
        new_lines.append('        else:\n')
        new_lines.append('            try:\n')
        new_lines.append('                x_dpi = int(dpi_val.split("x")[0].strip())\n')
        new_lines.append('                if canon_dt == "passport_photo":\n')
        new_lines.append('                    if x_dpi < 96 or x_dpi > 300: errors.append(f"DPI: FAIL - {x_dpi}x{x_dpi} DPI (required 96-300)")\n')
        new_lines.append('                    else: errors.append(f"DPI: PASS - {x_dpi}x{x_dpi} DPI (required 96-300)")\n')
        new_lines.append('                else:\n')
        new_lines.append('                    if x_dpi < 96 or x_dpi > 200: errors.append(f"DPI: FAIL - {x_dpi}x{x_dpi} DPI (required 96-200)")\n')
        new_lines.append('                    else: errors.append(f"DPI: PASS - {x_dpi}x{x_dpi} DPI (required 96-200)")\n')
        new_lines.append('            except:\n')
        new_lines.append('                errors.append("DPI: FAIL - Invalid DPI metadata format")\n')
        new_lines.append('                \n')
        new_lines.append('        has_fail = any("FAIL" in e for e in errors)\n')
        new_lines.append('        err_str = "&#10;".join(errors)\n')
        new_lines.append('        \n')
        new_lines.append('        if has_fail:\n')
        new_lines.append('            return format_html(\'<span style="color: #dc3545; font-weight: bold; cursor: help;" title="{}">\u2715 FAIL</span>\', err_str)\n')
        new_lines.append('        return format_html(\'<span style="color: #198754; font-weight: bold; cursor: help;" title="{}">\u2713 PASS</span>\', err_str)\n')
        new_lines.append('    validation_status.short_description = "Validation"\n')
        
    elif skip and line.startswith('    validation_status.short_description = "Validation"'):
        skip = False
    elif not skip:
        new_lines.append(line)

with open('registrations/admin.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

