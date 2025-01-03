$(document).ready(function() {
    // Initialize select2 dropdowns
    $('.select2').select2();
    
    let schemas = [];
    let sourceEntities = [];
    let targetEntities = [];

    // Fetch schemas
    $.get('/api/schemas/', function(data) {
        schemas = data;
        const sourceSchemaSelect = $('#sourceSchema');
        data.forEach(schema => {
            sourceSchemaSelect.append(new Option(schema.name, schema.id));
        });
    });

    // Source schema change handler
    $('#sourceSchema').on('change', function() {
        const schemaId = $(this).val();
        const schema = schemas.find(s => s.id == schemaId);
        
        // Reset dependent fields
        $('#sourceEntity').empty().append(new Option('Select Source Entity', '')).prop('disabled', !schema);
        $('#targetSchema').empty().append(new Option('Select Target Schema', '')).prop('disabled', !schema);
        $('#targetEntities').empty().prop('disabled', true);
        $('#matchButton').prop('disabled', true);
        
        if (schema) {
            sourceEntities = schema.entities;
            sourceEntities.forEach(entity => {
                $('#sourceEntity').append(new Option(entity.name, entity.id));
            });
            
            // Update target schema options
            const targetSchemaSelect = $('#targetSchema');
            schemas
                .filter(s => s.id != schemaId)
                .forEach(schema => {
                    targetSchemaSelect.append(new Option(schema.name, schema.id));
                });
        }
    });

    // Target schema change handler
    $('#targetSchema').on('change', function() {
        const schemaId = $(this).val();
        const schema = schemas.find(s => s.id == schemaId);
        
        $('#targetEntities').empty().prop('disabled', !schema);
        $('#matchButton').prop('disabled', true);
        
        if (schema) {
            targetEntities = schema.entities;
            targetEntities.forEach(entity => {
                $('#targetEntities').append(new Option(entity.name, entity.id));
            });
        }
    });

    // Source entity change handler
    $('#sourceEntity').on('change', function() {
        updateMatchButton();
    });

    // Target entities change handler
    $('#targetEntities').on('change', function() {
        updateMatchButton();
    });

    function updateMatchButton() {
        const sourceEntitySelected = $('#sourceEntity').val();
        const targetEntitiesSelected = $('#targetEntities').val()?.length > 0;
        $('#matchButton').prop('disabled', !sourceEntitySelected || !targetEntitiesSelected);
    }

    // Match button click handler
    $('#matchButton').on('click', function() {
        const button = $(this);
        button.prop('disabled', true).text('Matching...');
        
        const sourceEntityId = $('#sourceEntity').val();
        const targetEntityIds = $('#targetEntities').val();
        const matchPromises = [$.ajax({
                url: '/api/match-entities/',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    source_entity_id: sourceEntityId,
                    target_entity_ids: targetEntityIds,
                    model_name: 'openai'
                })
            })];

        Promise.all(matchPromises)
            .then(results => {
                $('#resultsBody').empty();
                results.forEach(result => {
                    Object.entries(result.field_mappings).forEach(([fieldName, matches]) => {
                        const sortedMatches = [...matches].sort((a, b) => b.score - a.score);
                        const topMatch = sortedMatches[0];
                        const otherMatches = sortedMatches.slice(1);

                        const row = $('<tr>');
                        row.append($('<td>').text(fieldName));
                        row.append($('<td>').text(
                            `${topMatch.target_field_name} (${topMatch.score.toFixed(2)})`
                        ));
                        row.append($('<td>').text(
                            otherMatches
                                .map(m => `${m.target_field_name} (${m.score.toFixed(2)})`)
                                .join(', ')
                        ));

                        $('#resultsBody').append(row);
                    });
                });
            })
            .catch(error => {
                console.error('Error matching entities:', error);
                alert('Error matching entities. Please try again.');
            })
            .finally(() => {
                button.prop('disabled', false).text('Match');
            });
    });
});
