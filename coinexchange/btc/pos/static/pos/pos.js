
// var context = {var1: "test variable"}
// T.render('pos/new_sale', function(t){
	// $('#handlebar-test').html(t(context));
// });

function toFixed(value, precision) {
    var precision = precision || 0,
    neg = value < 0,
    power = Math.pow(10, precision),
    value = Math.round(value * power),
    integral = String((neg ? Math.ceil : Math.floor)(value / power)),
    fraction = String((neg ? -value : value) % power),
    padding = new Array(Math.max(precision - fraction.length, 0) + 1).join('0');

    return precision ? integral + '.' +  padding + fraction : integral;
}
function isNumber(n) {
  return !isNaN(parseFloat(n)) && isFinite(n);
}

function show_alert(err_div, message, alert_class){
	if(!alert_class){
		alert_class="alert-error";
	}
	var alert_html = {alert_type: alert_class, message: message};
	T.render('pos/alert', function(t){
		err_div.append(t(alert_html));
	});
}

var xmpp_connection = null;
$(document).ready(function(){
	$.ajax({
		url: '/account/api/xmpp',
		dataType: 'json',
		success: function(settings){
			xmpp_connection = new Strophe.Connection(settings.bosh_url);
			xmpp_connection.connect(settings.username, settings.password, function(status){
				if(status == Strophe.Status.CONNECTING){
					show_alert($('#status_messages'), "XMPP Connecting");
				}else if(status==Strophe.Status.CONNECTED){
					show_alert($('#status_messages'), "XMPP Connected!");
				}else{
					show_alert($('#status_messages'), "XMPP Encountered an unexpected connection error state: "+status);
				}
			});
		},
		error: function(xhr, textStatus, err){
			show_alert($('#status_messages'), "Could not get XMPP credentials: "+textStatus+'\n'+err);
		}
	});
});

var exchange_rate = 810;

var item_count=1;
$('#test-btn').bind("click", function(){
	var itemhtml = '<div class="span2"><h4>Inserted Item'+ item_count++ +'</h4></div>';
	$('#sale_status_area').prepend(itemhtml);
});

$('#newSaleButton').bind("click", function(){
	$('#newSaleQR').html("");
	var sale_form = $('#newSaleForm')[0];
	$(sale_form).show();
	sale_form.reset();
});

$('#newSaleSubmit').bind("click", function(){
	var sale_form = $($('#newSaleForm')[0]);
	var reference = $(sale_form.find('[name=reference]')[0]).val();
	var currency = "USD";
	var amount = $(sale_form.find('[name=amount]')[0]).val();
	var btc = (amount/exchange_rate).toFixed(8);
	
	if(!isNumber(amount)){
		show_alert($('#newSaleErrors'), "Amount did not contain a number.");
		return;
	}

	var send_address = "1EDuyfcLXwcu7osRtkxGmY6oSRXssy3fHt";
	var qr = qrcode(4, 'M');
	var request_text = 'bitcoin:'+send_address+'?amount='+btc;
	qr.addData(request_text);
	qr.make();
	
	$('#newSaleQR').html(qr.createImgTag(7,5));
	$('#newSaleQR').append('<br/>'+reference+' - '+amount+' '+currency+'<br/>('+btc+' BTC)<br/>'+request_text);
	sale_form.hide();
	$('#newSaleErrors').html('');
	var sales_tx_info = {
		reference: reference,
		amount: amount+' '+currency,
		status: 'pending',
		style: "",
		extra_class: "btn btn-warning"
		};
	T.render('pos/sales_transaction', function(t){
		$('#sale_status_area').prepend(t(sales_tx_info));
	});
});
