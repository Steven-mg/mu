// Configurar el modal de rotación
document.addEventListener('DOMContentLoaded', function() {
    // Fallback: define global alert helpers if not present
    if (typeof window.mostrarAlerta !== 'function') {
        window.mostrarAlerta = function(mensaje, tipo, id = null) {
            const modalBody = document.querySelector('#rotarAnimales .modal-body') || document.body;
            let container = document.getElementById('alertContainer') || document.getElementById('alertContainerRotacion');
            if (!container) {
                container = document.createElement('div');
                container.id = 'alertContainerRotacion';
                modalBody.prepend(container);
            }
            const alerta = document.createElement('div');
            alerta.className = `alert alert-${tipo}`;
            if (id) alerta.id = id;
            let icono = '';
            switch (tipo) {
                case 'success': icono = '<i class="fas fa-check-circle me-2"></i>'; break;
                case 'danger': icono = '<i class="fas fa-exclamation-circle me-2"></i>'; break;
                case 'info': icono = '<i class="fas fa-spinner fa-spin me-2"></i>'; break;
                default: icono = '';
            }
            alerta.innerHTML = icono + mensaje;
            container.appendChild(alerta);
        };
    }
    if (typeof window.eliminarAlerta !== 'function') {
        window.eliminarAlerta = function(id) {
            const alerta = document.getElementById(id);
            if (alerta) alerta.remove();
        };
    }
    // Snapshot de opciones originales del selector de grupos
    const grupoSelectEl = document.getElementById('grupoAnimal');
    const originalGrupoOptions = (() => {
        const arr = [];
        if (grupoSelectEl) {
            Array.from(grupoSelectEl.options).forEach(opt => {
                arr.push({ value: opt.value, text: opt.textContent });
            });
        }
        return arr;
    })();

    // Reconstruir opciones del selector de grupos según acción
    function rebuildGrupoOptions(action, gruposEnPotreroIds) {
        const select = document.getElementById('grupoAnimal');
        if (!select || !originalGrupoOptions.length) return;

        const enPotreroSet = new Set((gruposEnPotreroIds || []).map(id => String(id)));

        // Limpiar y añadir opción vacía por defecto
        select.innerHTML = '';
        const optDefault = document.createElement('option');
        optDefault.value = '';
        optDefault.textContent = 'Seleccione un grupo';
        select.appendChild(optDefault);

        // Agregar opciones filtradas
        originalGrupoOptions.forEach(({ value, text }) => {
            if (!value) return; // saltar opción vacía original
            const estaEnPotrero = enPotreroSet.has(String(value));
            // En 'agregar': mostrar solo los que NO están en el potrero
            // En 'rotar': mostrar solo los que SÍ están en el potrero
            const incluir = action === 'agregar' ? !estaEnPotrero : estaEnPotrero;
            if (incluir) {
                const opt = document.createElement('option');
                opt.value = value;
                opt.textContent = text;
                select.appendChild(opt);
            }
        });
    }

    // Capturar el ID del potrero cuando se abre el modal
    const rotarAnimalesModal = document.getElementById('rotarAnimales');
    if (rotarAnimalesModal) {
        rotarAnimalesModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const potreroId = button.getAttribute('data-potrero-id');
            const action = button.getAttribute('data-action') || 'rotar';
            document.getElementById('potreroIdRotacion').value = potreroId;
            const accionInput = document.getElementById('accionRotacion');
            if (accionInput) accionInput.value = action;
            // Actualizar título del modal según acción
            const titleEl = document.getElementById('rotarAnimalesLabel');
            if (titleEl) {
                titleEl.textContent = action === 'agregar' ? 'Agregar Grupo al Potrero' : 'Rotar Grupo Animal';
            }
            
            // Establecer la fecha de inicio como la fecha actual
            const fechaInicio = document.getElementById('fechaInicio');
            const hoy = new Date().toISOString().split('T')[0];
            fechaInicio.value = hoy;

            // Restricción de Tipo de Uso en modo 'agregar': limitar al default del potrero actual
            const tipoUsoSelect = document.getElementById('tipoUso');
            if (tipoUsoSelect) {
                // Cachear opciones originales si aún no se ha hecho
                if (!tipoUsoSelect.dataset.originalOptions) {
                    const opts = Array.from(tipoUsoSelect.options).map(o => ({ value: o.value, text: o.textContent }));
                    tipoUsoSelect.dataset.originalOptions = JSON.stringify(opts);
                }
                if (action === 'agregar') {
                    fetch(`/api/potrero/default-tipo-uso?potrero_id=${potreroId}`)
                        .then(r => r.json())
                        .then(data => {
                            if (data && data.success && data.default_tipo_uso) {
                                const labelMap = {
                                    'pastoreo': 'Pastoreo',
                                    'descanso': 'Descanso',
                                    'siembra': 'Siembra',
                                    'fertilización': 'Fertilización',
                                    'mantenimiento': 'Mantenimiento'
                                };
                                tipoUsoSelect.innerHTML = '';
                                const unica = document.createElement('option');
                                unica.value = data.default_tipo_uso;
                                unica.textContent = labelMap[data.default_tipo_uso] || data.default_tipo_uso;
                                unica.selected = true;
                                tipoUsoSelect.appendChild(unica);
                            }
                        })
                        .catch(err => console.error('Error obteniendo default tipo de uso del potrero actual:', err));
                }
            }

            // Filtrar/poblar grupos según acción
            if (action === 'rotar') {
                // Poblar con los grupos presentes en el potrero actual desde API
                const select = document.getElementById('grupoAnimal');
                if (select) {
                    // Reset y default
                    select.innerHTML = '';
                    const def = document.createElement('option');
                    def.value = '';
                    def.textContent = 'Seleccione un grupo';
                    select.appendChild(def);
                }
                fetch(`/api/grupos-activos-por-potrero?potrero_id=${potreroId}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data && data.success && Array.isArray(data.grupos)) {
                            const selectEl = document.getElementById('grupoAnimal');
                            // Construir solo los grupos presentes
                            data.grupos.forEach(g => {
                                const opt = document.createElement('option');
                                opt.value = String(g.id);
                                opt.textContent = g.nombre;
                                selectEl.appendChild(opt);
                            });
                        } else {
                            // Fallback al filtrado local si falla API
                            if (typeof gruposEnPotrero !== 'undefined' && Array.isArray(gruposEnPotrero)) {
                                rebuildGrupoOptions('rotar', gruposEnPotrero);
                            }
                        }
                    })
                    .catch(() => {
                        if (typeof gruposEnPotrero !== 'undefined' && Array.isArray(gruposEnPotrero)) {
                            rebuildGrupoOptions('rotar', gruposEnPotrero);
                        }
                    });
            } else {
                // 'agregar': mostrar todos menos los presentes
                if (typeof gruposEnPotrero !== 'undefined' && Array.isArray(gruposEnPotrero)) {
                    rebuildGrupoOptions('agregar', gruposEnPotrero);
                }
            }

            // Limpiar fecha fin en modo agregar (en curso)
            const fechaFin = document.getElementById('fechaFin');
            if (fechaFin) {
                fechaFin.value = '';
            }

            // Mostrar/ocultar selector de destino según acción
            const destinoGroup = document.getElementById('potreroDestinoGroup');
            const destinoSelect = document.getElementById('potreroDestino');
            const nuevoGrupoBtn = document.getElementById('btnNuevoGrupo');
            if (destinoGroup) {
                destinoGroup.classList.toggle('d-none', action !== 'rotar');
            }
            // Mostrar el botón "+" solo en modo agregar
            if (nuevoGrupoBtn) {
                nuevoGrupoBtn.classList.toggle('d-none', action !== 'agregar');
            }

            // Cargar potreros disponibles de la finca para seleccionar destino (solo si rotar)
            if (action === 'rotar' && destinoSelect && typeof fincaId !== 'undefined' && fincaId) {
                // Limpiar y set default
                destinoSelect.innerHTML = '';
                const optDefault = document.createElement('option');
                optDefault.value = '';
                optDefault.textContent = 'Seleccione potrero destino';
                destinoSelect.appendChild(optDefault);

                fetch(`/api/potreros-por-finca?finca_id=${fincaId}&exclude_descanso=1`)
                    .then(r => r.json())
                    .then(items => {
                        items.forEach(([id, nombre]) => {
                            // Excluir el mismo potrero como destino si se desea cambiar
                            if (String(id) === String(potreroId)) return;
                            const opt = document.createElement('option');
                            opt.value = id;
                            opt.textContent = nombre;
                            destinoSelect.appendChild(opt);
                        });
                        // Cachear opciones originales de tipo de uso
                        const tipoUsoSelect = document.getElementById('tipoUso');
                        const originalTipoUsoOptions = (() => {
                            if (!tipoUsoSelect) return [];
                            if (tipoUsoSelect.dataset.originalOptions) {
                                try { return JSON.parse(tipoUsoSelect.dataset.originalOptions); } catch (e) { /* fall back below */ }
                            }
                            const opts = Array.from(tipoUsoSelect.options).map(o => ({ value: o.value, text: o.textContent }));
                            tipoUsoSelect.dataset.originalOptions = JSON.stringify(opts);
                            return opts;
                        })();
                        // Agregar listener para limitar el tipo de uso al del potrero destino
                        destinoSelect.addEventListener('change', function() {
                            const destId = destinoSelect.value;
                            const tipoUsoSelect = document.getElementById('tipoUso');
                            if (!tipoUsoSelect) return;
                            // Si no hay destino seleccionado, restaurar opciones originales
                            if (!destId) {
                                tipoUsoSelect.innerHTML = '';
                                originalTipoUsoOptions.forEach(({ value, text }) => {
                                    const opt = document.createElement('option');
                                    opt.value = value;
                                    opt.textContent = text;
                                    tipoUsoSelect.appendChild(opt);
                                });
                                return;
                            }
                            fetch(`/api/potrero/default-tipo-uso?potrero_id=${destId}`)
                                .then(r => r.json())
                                .then(data => {
                                    if (data && data.success && data.default_tipo_uso) {
                                        const labelMap = {
                                            'pastoreo': 'Pastoreo',
                                            'descanso': 'Descanso',
                                            'siembra': 'Siembra',
                                            'fertilización': 'Fertilización',
                                            'mantenimiento': 'Mantenimiento'
                                        };
                                        tipoUsoSelect.innerHTML = '';
                                        const unica = document.createElement('option');
                                        unica.value = data.default_tipo_uso;
                                        unica.textContent = labelMap[data.default_tipo_uso] || data.default_tipo_uso;
                                        unica.selected = true;
                                        tipoUsoSelect.appendChild(unica);
                                    }
                                })
                                .catch(err => console.error('Error obteniendo default tipo de uso:', err));
                        });
                    })
                    .catch(err => console.error('Error cargando potreros destino:', err));
            }
        });
    }
    
    // Guardar rotación
    const btnGuardarRotacion = document.getElementById('btnGuardarRotacion');
    if (btnGuardarRotacion) {
        btnGuardarRotacion.addEventListener('click', function() {
            const form = document.getElementById('formRotacion');
            const formData = {
                potrero_id: document.getElementById('potreroIdRotacion').value,
                // Enviar explícitamente el potrero de origen para cerrar la rotación previa
                potrero_origen_id: document.getElementById('potreroIdRotacion').value,
                grupo_animal_id: document.getElementById('grupoAnimal').value,
                fecha_inicio: document.getElementById('fechaInicio').value,
                fecha_fin: document.getElementById('fechaFin').value || null,
                tipo_uso: document.getElementById('tipoUso').value,
                observaciones: document.getElementById('observaciones').value,
                potrero_destino_id: (document.getElementById('potreroDestino') ? document.getElementById('potreroDestino').value : null)
            };

            // Si la acción es rotar, usar el potrero destino como potrero_id para la nueva rotación
            const accionInput = document.getElementById('accionRotacion');
            const esRotar = accionInput ? (accionInput.value === 'rotar') : true;
            if (esRotar && formData.potrero_destino_id) {
                formData.potrero_id = formData.potrero_destino_id;
            }
            
            // Validar campos requeridos
            if (!formData.potrero_id || !formData.grupo_animal_id || !formData.fecha_inicio || !formData.tipo_uso) {
                mostrarAlerta('Por favor complete todos los campos requeridos', 'danger', 'alertaRotacion');
                return;
            }

            // Validar potrero destino cuando acción sea rotar
            const destinoSelect = document.getElementById('potreroDestino');
            if (esRotar && destinoSelect && (destinoSelect.value === '' || destinoSelect.value === null)) {
                mostrarAlerta('Seleccione un potrero destino disponible para rotar el grupo', 'danger', 'alertaRotacion');
                return;
            }
            
            // Enviar datos al servidor
            fetch('/guardar-rotacion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': (typeof csrfToken !== 'undefined' ? csrfToken : '')
                },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Cerrar modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('rotarAnimales'));
                    modal.hide();
                    
                    // Mostrar mensajes según capacidad
                    if (data.excede_capacidad) {
                        const msg = `Capacidad excedida: ${data.ocupacion_total} / ${data.capacidad} animales`;
                        mostrarAlerta(msg, 'danger', 'alertaGeneral');
                    } else {
                        mostrarAlerta(data.message, 'success', 'alertaGeneral');
                    }
                    
                    // Recargar la página para mostrar la nueva rotación
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    mostrarAlerta(data.message, 'danger', 'alertaRotacion');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                mostrarAlerta('Error al guardar la rotación', 'danger', 'alertaRotacion');
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
            
            // Redirigir a la lista/gestión de grupos de la finca
            if (typeof fincaId === 'undefined' || !fincaId) {
                console.error('fincaId no disponible para redirigir a grupos de finca');
                return;
            }
            window.location.href = '/finca/' + fincaId + '/grupos';
            
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