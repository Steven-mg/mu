// Configurar el modal de rotación
document.addEventListener('DOMContentLoaded', function() {
    // Capturar el ID del potrero cuando se abre el modal
    const rotarAnimalesModal = document.getElementById('rotarAnimales');
    if (rotarAnimalesModal) {
        rotarAnimalesModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const potreroId = button.getAttribute('data-potrero-id');
            document.getElementById('potreroIdRotacion').value = potreroId;
            
            // Establecer la fecha de inicio como la fecha actual
            const fechaInicio = document.getElementById('fechaInicio');
            const hoy = new Date().toISOString().split('T')[0];
            fechaInicio.value = hoy;
        });
    }
    
    // Guardar rotación
    const btnGuardarRotacion = document.getElementById('btnGuardarRotacion');
    if (btnGuardarRotacion) {
        btnGuardarRotacion.addEventListener('click', function() {
            const form = document.getElementById('formRotacion');
            const formData = {
                potrero_id: document.getElementById('potreroIdRotacion').value,
                grupo_animal_id: document.getElementById('grupoAnimal').value,
                fecha_inicio: document.getElementById('fechaInicio').value,
                fecha_fin: document.getElementById('fechaFin').value || null,
                tipo_uso: document.getElementById('tipoUso').value,
                observaciones: document.getElementById('observaciones').value
            };
            
            // Validar campos requeridos
            if (!formData.potrero_id || !formData.grupo_animal_id || !formData.fecha_inicio || !formData.tipo_uso) {
                mostrarAlerta('alertaRotacion', 'danger', 'Por favor complete todos los campos requeridos');
                return;
            }
            
            // Enviar datos al servidor
            fetch('/guardar-rotacion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Cerrar modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('rotarAnimales'));
                    modal.hide();
                    
                    // Mostrar mensaje de éxito
                    mostrarAlerta('alertaGeneral', 'success', data.message);
                    
                    // Recargar la página para mostrar la nueva rotación
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    mostrarAlerta('alertaRotacion', 'danger', data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                mostrarAlerta('alertaRotacion', 'danger', 'Error al guardar la rotación');
            });
        });
    }
    
    // Añadir al final del evento DOMContentLoaded existente
    
    // Manejar el botón de nuevo grupo animal
    const btnNuevoGrupo = document.getElementById('btnNuevoGrupo');
    if (btnNuevoGrupo) {
        btnNuevoGrupo.addEventListener('click', function() {
            // Cerrar el modal actual
            const modalRotacion = bootstrap.Modal.getInstance(document.getElementById('rotarAnimales'));
            if (modalRotacion) {
                modalRotacion.hide();
            }
            
            // Redirigir a la página de creación de grupo animal o abrir otro modal
            // Opción 1: Redirigir a una página
            window.location.href = '/crear-grupo-animal?finca_id=' + fincaId + '&redirect=gestionarfinca';
            
            // Opción 2: Abrir otro modal (descomenta esta sección si prefieres usar un modal)
            /*
            setTimeout(() => {
                const nuevoGrupoModal = new bootstrap.Modal(document.getElementById('crearGrupoAnimal'));
                nuevoGrupoModal.show();
            }, 500);
            */
        });
    }
});