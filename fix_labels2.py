import re

with open('templates/registration/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Country
content = content.replace(
'''                    <div class="form-floating">
                            <input type="text" class="form-control" value="India" disabled readonly>
                            <input type="hidden" id="country" name="country" value="{% for c in countries %}{% if c.name == 'India' %}{{ c.id }}{% endif %}{% endfor %}">
                            <label>Country *</label>
                        </div>''',
'''                    <div class="form-group">
                        <label class="fw-bold mb-2">Country *</label>
                        <input type="text" class="form-control" value="India" disabled readonly>
                        <input type="hidden" id="country" name="country" value="{% for c in countries %}{% if c.name == 'India' %}{{ c.id }}{% endif %}{% endfor %}">
                    </div>'''
)

# Custom Stream
content = content.replace(
'''                    <div class="form-floating" id="custom_stream_container" style="display: none;">
                        <input type="text" class="form-control" id="custom_stream" name="custom_stream" placeholder="Enter custom stream" value="{{ form_data.custom_stream }}">
                        <label for="custom_stream">Specify Stream *</label>
                        <div class="invalid-feedback">Stream name is required (3-100 chars, no special characters).</div>
                    </div>''',
'''                    <div class="form-group" id="custom_stream_container" style="display: none;">
                        <label for="custom_stream" class="fw-bold mb-2">Specify Stream *</label>
                        <input type="text" class="form-control" id="custom_stream" name="custom_stream" placeholder="Enter custom stream" value="{{ form_data.custom_stream }}">
                        <div class="invalid-feedback">Stream name is required (3-100 chars, no special characters).</div>
                    </div>'''
)

# Institution
content = content.replace(
'''                    <div class="form-floating">
                        <input type="text" class="form-control" id="institution" name="institution" placeholder="[ Enter institution name ]" value="{{ form_data.institution }}" required>
                        <label for="institution">Institution *</label>
                    </div>''',
'''                    <div class="form-group">
                        <label for="institution" class="fw-bold mb-2">Institution *</label>
                        <input type="text" class="form-control" id="institution" name="institution" placeholder="[ Enter institution name ]" value="{{ form_data.institution }}" required>
                    </div>'''
)

# Hall Ticket
content = content.replace(
'''                    <div class="col-md-6 form-floating">
                        <input type="text" class="form-control text-uppercase" id="hall_ticket_number" name="hall_ticket_number" placeholder="[ Enter hall ticket number ]" value="{{ form_data.hall_ticket_number }}" required>
                        <label for="hall_ticket_number" class="ms-2">Hall Ticket Number *</label>
                        <div class="invalid-feedback ms-2">Enter a valid 10-15 character alphanumeric Hall Ticket Number.</div>
                    </div>''',
'''                    <div class="col-md-6 form-group">
                        <label for="hall_ticket_number" class="fw-bold mb-2">Hall Ticket Number *</label>
                        <input type="text" class="form-control text-uppercase" id="hall_ticket_number" name="hall_ticket_number" placeholder="[ Enter hall ticket number ]" value="{{ form_data.hall_ticket_number }}" required>
                        <div class="invalid-feedback">Enter a valid 10-15 character alphanumeric Hall Ticket Number.</div>
                    </div>'''
)

with open('templates/registration/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done 2')
