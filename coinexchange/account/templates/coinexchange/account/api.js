
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
	_display_status('alert-danger', message);
}

function display_success(message){
	_display_status('alert-success', message);
}

function display_warning(message){
	_display_status('alert-warning', message);
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
var e_alert;
$(function(){
	$('.coinexchange-help').bind('click', function(e){
		e_alert = e;
		var doc = $(e.currentTarget).attr('help-document');
		var title = $(e.currentTarget).attr('help-title');
		// alert(doc);
		$('#help-modal').modal();
		$('#help-modal-header').html(title);
		$('#help-modal-body').html("Loading... ("+doc+")");
		help_url = "/static/coinexchange/help/"+doc+".html";
		$.ajax({
			type: 'get',
			url: help_url,
			success: function(data, textStatus, jqXHR){
				$('#help-modal-body').html(data);
			},
			error: function(jqXHR, textStatus, errorThrown){
				$('#help-modal-body').html("Error loading help document: "+errorThrown+"<br/>"+help_url);
			}
		});
		
	});
	$('a[data-toggle="tab"]').on('shown.bs.tab', function(e){
		debug_e = e;
		var tab_id = $(e.target).attr('href');
		localStorage.setItem('lastTab', tab_id);
	});
	var lastTab = localStorage.getItem('lastTab');
	if (lastTab){
		$('a[data-toggle="tab"][href="'+lastTab+'"]').tab('show');
	}
});

$.fn.datepicker.defaults.format = "mm/dd/yyyy";
