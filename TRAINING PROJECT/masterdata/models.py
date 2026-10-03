from django.db import models

class MasterBaseModel(models.Model):
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['display_order', 'id']

class Country(MasterBaseModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    iso_code = models.CharField(max_length=3, unique=True, blank=True, null=True)
    
    def __str__(self):
        return self.name

class State(MasterBaseModel):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states', null=True, blank=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return self.name

class District(MasterBaseModel):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    
    def __str__(self):
        return f"{self.name} ({self.state.name})"

class Religion(MasterBaseModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    def __str__(self):
        return self.name

class MaritalStatus(MasterBaseModel):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class ExServiceStatus(MasterBaseModel):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class Community(MasterBaseModel):
    name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return self.name

class Occupation(MasterBaseModel):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name

class Qualification(MasterBaseModel):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return self.name

class YearOfStudy(MasterBaseModel):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class Program(MasterBaseModel):
    name = models.CharField(max_length=200, unique=True)
    duration = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class ApplicationStatus(MasterBaseModel):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return self.name

class VerificationStatus(MasterBaseModel):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return self.name

class TrainingPartner(MasterBaseModel):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    def __str__(self):
        return self.name

class BatchCode(MasterBaseModel):
    training_partner = models.ForeignKey(TrainingPartner, on_delete=models.CASCADE, related_name='batches')
    code = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.code

