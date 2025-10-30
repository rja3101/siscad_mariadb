from django import forms


class ImportStudentsForm(forms.Form):
    """Formulario para importar estudiantes"""
    file = forms.FileField(
        label='Archivo XLSX',
        help_text='Sube un archivo Excel con los datos de los estudiantes',
        widget=forms.FileInput(attrs={
            'accept': '.xlsx',
            'class': 'form-control'
        })
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if not file:
            raise forms.ValidationError("Debes subir un archivo")
        
        # Validar extensión
        if not file.name.endswith('.xlsx'):
            raise forms.ValidationError("El archivo debe ser .xlsx")
        
        # Validar tamaño (máx 5MB)
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("El archivo no debe exceder 5MB")
        
        return file


class ImportEnrollmentsForm(forms.Form):
    """Formulario para importar matrículas"""
    file = forms.FileField(
        label='Archivo XLSX',
        help_text='Sube un archivo Excel con los datos de las matrículas',
        widget=forms.FileInput(attrs={
            'accept': '.xlsx',
            'class': 'form-control'
        })
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if not file:
            raise forms.ValidationError("Debes subir un archivo")
        
        # Validar extensión
        if not file.name.endswith('.xlsx'):
            raise forms.ValidationError("El archivo debe ser .xlsx")
        
        # Validar tamaño (máx 5MB)
        if file.size > 5 * 1024 * 1024:
            raise forms.ValidationError("El archivo no debe exceder 5MB")
        
        return file