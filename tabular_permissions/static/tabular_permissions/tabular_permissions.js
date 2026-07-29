window.onload = function() {
  (function($){
        $(".related-widget-wrapper:has(table)").addClass('related-widget-wrapper-user-permissions');
        $('table.tabular-permissions:not(.processed)').each(function (){
            var $table = $(this).addClass('processed');
            $table.find('input.select-all.select-column').on('change', function () {
                var $el = $(this),
                    state = $el.prop('checked');
                // search for related columns.
                $table.find("tr td." + $el.data('permission')).find('input').each(function (i, e) {
                    $(e).prop('checked', state)
                });
            }).each(function (){
                // keeps all columns checked.
                var $el = $(this);
                var $inputs = $table.find("tr td." + $el.data('permission')).find('input');
                $el.prop('checked', $inputs.length === $inputs.filter(function () {
                    return $(this).is(":checked");
                }).length);
            })

            $table.find('input.select-all.select-row').on('change', function(){
                var $el = $(this);
                $el.parents('tr').find('.checkbox').not('.select-all').each(function(i,elem){
                    $(elem).prop('checked', $el.prop('checked'));
                })
            }).each(function (){
                // keeps all rows checked.
                var $el = $(this),
                    $inputs = $el.parents('tr').find('input.model-' + $el.data("model-name")).not('.select-all');
                $el.prop('checked', $inputs.length === $inputs.filter(function () {
                    return $(this).is(":checked");
                }).length);
            });

            // Registering the submit handler is deferred on purpose. FilteredSelectMultiple
            // also binds a submit handler that keeps only the options present in its own
            // cache, so a handler registered before it has its options stripped again.
            // Deferring puts this one last, after the cleanup, so the permissions picked in
            // the table survive the submit.
            setTimeout(function () {
                $('form').on('submit', function () {
                    var user_perms = [];
                    var table_permissions = $table;
                    var input_name = table_permissions.attr('data-input-name');
                    table_permissions.find("input[type=checkbox]").not('.select-all').each(function (i, elem) {
                        var $elem = $(elem);
                        if ($(elem).prop('checked')) {
                            user_perms.push($elem.attr('data-perm-id'))
                        }
                    });
                    var user_group_permissions = $('[name=' + input_name +']');
                    var output = [];
                    $.each(user_perms, function (key, value) {
                        output.push('<option value="' + value + '" selected="selected" style="display:none"></option>');
                    });
                    user_group_permissions.append(output);
                });
            }, 0);
        })
    })(django.jQuery);
};
