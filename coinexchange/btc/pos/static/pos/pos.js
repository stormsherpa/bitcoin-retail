
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

function showPosUI(state){
	if(state){
		$('#posUI').show();
		$('#posUILoading').hide();
	}else{
		$('#posUI').hide();
		$('#posUILoading').show();
	}
}

///////////////////////////////
////  Sales Transaction Objects
///////////////////////////////
var SalesTransactions = new Array();

function SalesTransaction(reference, amount){
	this.request_text;
	this.reference = reference;
	this.amount = amount;
	this.fiat_amount;
	this.btc_amount;
	this.status = 'pending';
	this.sale_id;
	this.html_element;
}

SalesTransaction.prototype.newsaleUpdate = function(data){
	this.fiat_amount = data.fiat_amount+' '+data.currency;
	this.request_text = 'bitcoin:'+data.address+'?amount='+data.btc_amount;
	this.btc_amount = data.btc_amount;
	this.sale_id = data.sale_id;
	SalesTransactions[this.sale_id] = this;
	return this;
};

SalesTransaction.prototype.generateQR = function(){
	var qr = qrcode(4, 'M');
	qr.addData(this.request_text);
	qr.make();
	return qr.createImgTag(7,5);
};

SalesTransaction.prototype.get_html_element = function(){
	return $('div[saleID='+this.sale_id+']')[0];
};
///////////////////////////////

var xmpp_connection = null;

function onMessage(msg){
	var to=msg.getAttribute('to');
	var from=msg.getAttribute('from');
	var type=msg.getAttribute('type');
	var elems = msg.getElementsByTagName('body');
	if(type=="chat" && elems.length > 0){
		var body=elems[0];
		message = from+': '+Strophe.getText(body);
		show_alert($('#status_messages'), message, "alert-success");
	}
	return true;
}

function xmpp_onConnect(status){
	if(status == Strophe.Status.CONNECTING){
		// show_alert($('#status_messages'), "XMPP Connecting");
	}else if(status==Strophe.Status.CONNECTED){
		xmpp_connection.send($pres().tree());
		xmpp_connection.addHandler(onMessage, null, 'message', null, null, null);
		showPosUI(true);
		// show_alert($('#status_messages'), "XMPP Connected!");
	}else if(status==Strophe.Status.CONNFAIL){
		show_alert($('#status_messages'), "XMPP Connection failed!");
	}else if(status==Strophe.Status.DISCONNECTING){
		show_alert($('#status_messages'), "XMPP Disconnecting...");
	}else if(status==Strophe.Status.DISCONNECTED){
		show_alert($('#status_messages'), "XMPP Disconnected!");
	}else{
		show_alert($('#status_messages'), "XMPP Encountered an unexpected connection error state: "+status);
	}
}

$(document).ready(function(){
	$.ajax({
		url: '/account/api/xmpp',
		dataType: 'json',
		success: function(settings){
			xmpp_connection = new Strophe.Connection(settings.bosh_url);
			xmpp_connection.connect(settings.username, settings.password, xmpp_onConnect);
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
	$('#newSaleQR').attr('thisSale', null);
	var sale_form = $('#newSaleForm')[0];
	$(sale_form).show();
	sale_form.reset();
});
$('#newSaleSubmit').bind("click", function(){
	var sale_form = $($('#newSaleForm')[0]);
	var reference = $(sale_form.find('[name=reference]')[0]).val();
	var amount = $(sale_form.find('[name=amount]')[0]).val();

	if(!isNumber(amount)){
		show_alert($('#newSaleErrors'), "Amount did not contain a number.");
		return;
	}

	var onSuccess = function(data, textStatus, xhr){
		sale_tx = new SalesTransaction(reference, amount);
		sale_tx.newsaleUpdate(data);
		$('#newSaleQR').attr('thisSale', data.sale_id);
		$('#newSaleQR').html(sale_tx.generateQR());
		$('#newSaleQR').append('<br/>'+reference+' - '+sale_tx.fiat_amount+'<br/>('+sale_tx.btc_amount+' BTC)<br/>'+sale_tx.request_text);
		$('#newSaleQR').append('<button id="closeNewSale" data-dismiss="modal" class="btn btn-primary">Close</button>');
		sale_form.hide();
		$('#newSaleErrors').html('');
		var sales_tx_info = {
			sale_tx: sale_tx,
			style: "",
			extra_class: "btn btn-warning",
			sale_id: data.sale_id
			};
		T.render('pos/sales_transaction', function(t){
			$('#sale_status_area').prepend(t(sales_tx_info));
		});
	};
	var onError = function(xhr, textStatus, errorThrown){
		show_alert($('#status_messages'), "Error creating new sale: "+errorThrown);
	};
	$.ajax({
		type: 'POST',
		url: '/account/api/newsale',
		data: {reference: reference, amount: amount},
		dataType: 'json',
		success: onSuccess,
		error: onError
	});
});
