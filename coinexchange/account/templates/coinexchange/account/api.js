
function load_form_fields(form){
	var post_vars = {};
	var input_list = form.find('input');
	for(var i=0; i< input_list.length; i++){
		var item = $(input_list[i]);
		if (item.attr('type') == 'checkbox'){
			if (item.is(':checked') ){
				post_vars[item.attr('name')] = item.val();
			}
		}else{
			post_vars[item.attr('name')] = item.val();
		}
	}
	var select_list = form.find('select');
	for(var i=0; i< select_list.length; i++){
		var item = $(select_list[i]);
		post_vars[item.attr('name')] = item.val();
	}
	return post_vars;
}

function clear_form_fields(form){
	form.trigger("reset");
}

function _display_status(error_class, message){
	xbtn = '<button type="button" class="close" data-dismiss="alert">&times;</button>';
	html = '<div class="span12 alert '+error_class+'">'+xbtn+message+'</div>';
	$('#status_messages').append(html);
}

function display_error(message){
	_display_status('alert-error', message);
}

function display_success(message){
	_display_status('alert-success', message);
}

function display_warning(message){
	_display_status('alert-block', message);
}

function display_info(message){
	_display_status('alert-info', message);
}

function AccountAPI(){}

AccountAPI.prototype.withdraw_bitcoin = function(form, id){
	post_vars = load_form_fields(form);
	$.ajax(
		{
			type: 'POST',
			url: "{% url 'api_withdrawl' %}",
			data: JSON.stringify(post_vars),
			success: function(data, textStatus, jqXHR){
				if (data.error){
					display_error(data.result);
				}else{
					display_success(data.result);
					clear_form_fields(form);
				}
			},
			error: function(jqXHR, textStatus, errorThrown){
				display_error("Error: " + textStatus);
			}
		});
	return false;
};


