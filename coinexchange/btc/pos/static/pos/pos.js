
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
	this.pending;
	this.sale_id;
	this.html_element;
}

SalesTransaction.prototype.newsaleUpdate = function(data){
	this.fiat_amount = data.fiat_amount+' '+data.currency;
	this.request_text = 'bitcoin:'+data.address+'?amount='+data.btc_amount;
	this.btc_amount = data.btc_amount;
	this.sale_id = data.sale_id;
	this.pending = data.pending;
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

function updateTxStatus(status, sale_id){
	var el = $('div[type=sales_tx][saleid='+sale_id+']');
	if(status == "confirmed"){
		el.animate({height: "toggle"}, 200, function(){
			el.find('div.panel').attr('class', 'panel panel-success');
			// el.attr("class", "col-md-2 bg-success");
			el.animate({height: "toggle"}, 200);
		});
	}else{
		var msg = "Unexpected transaction update status: "+status+"\nSaleID: "+sale_id;
		show_alert($('#status_messages'), msg, "alert-error");
		el.attr("class", "col-md-2 bg-error");
	}
}

function onConfirm(msg){
	var elems = msg.getElementsByTagName('confirm');
	if(elems.length > 0){
		var json_msg = $(elems[0]).text();
		var jmsg = JSON.parse(json_msg);
		updateTxStatus(jmsg.status, jmsg.sale_id);
		// show_alert($('#status_messages'), jmsg.status+' - '+jmsg.sale_id, "alert-success");
	}
	return true;
}

function xmpp_doConnect(){
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
}

function xmpp_onConnect(status){
	if(status == Strophe.Status.CONNECTING){
		show_alert($('#loadPosStatus'), "XMPP Connecting...", "alert-success");
		// show_alert($('#status_messages'), "XMPP Connecting");
	}else if(status==Strophe.Status.CONNECTED){
		show_alert($('#loadPosStatus'), "XMPP Connected!");
		xmpp_connection.send($pres().tree());
		// xmpp_connection.addHandler(onMessage, null, 'message', null, null, null);
		xmpp_connection.addHandler(onConfirm, "coinexchange:tx:confirm", 'message', null, null, null);
		showPosUI(true);
	}else if(status==Strophe.Status.CONNFAIL){
		show_alert($('#status_messages'), "XMPP Connection failed!");
		setTimeout(xmpp_doConnect, 5000);
	}else if(status==Strophe.Status.DISCONNECTING){
		show_alert($('#status_messages'), "XMPP Disconnecting...");
	}else if(status==Strophe.Status.DISCONNECTED){
		show_alert($('#status_messages'), "XMPP Disconnected!");
	}else{
		show_alert($('#status_messages'), "XMPP Encountered an unexpected connection error state: "+status);
	}
}
var last_sale_tx;
function add_sale_div(sale_tx){
	last_sale_tx = sale_tx;
	var extra_class = sale_tx.pending ? "bg-warning" : "bg-success";
	var sales_tx_info = {
		sale_tx: sale_tx,
		style: "",
		extra_class: extra_class,
		sale_id: sale_tx.sale_id
	};
	T.render('pos/sales_transaction', function(t){
		$('#sale_status_area').prepend(t(sales_tx_info));
		$('div[saleid='+sale_tx.sale_id+']').bind('click', function(){
			T.render('pos/sales_transaction_detail', function(td){
				var tx_detail = {qr_code: sale_tx.generateQR(), sale_tx: sale_tx};
				$('#ReviewSale').modal();
				$('h4#ReviewSaleModal').html("Review Transaction "+sale_tx.sale_id);
				$('#ReviewSaleBody').html(td(tx_detail));
			});
		});
	});
}

function load_sale_history_items(item_list){
	if(item_list.length>0){
		sale_id = item_list.shift();
		$.ajax({
			type: 'GET',
			url: '/account/api/sale/'+sale_id,
			dataType: 'json',
			success: function(data, textStatus, xhr){
				if(data.pending){
					sale_tx = new SalesTransaction(data.reference, data.fiat_amount);
					sale_tx.newsaleUpdate(data);
					add_sale_div(sale_tx);
				}
				load_sale_history_items(item_list);
			}
		});
	}
	// console.log(sale_id);
}

function load_sale_history(){
	console.log("test");
	$.ajax({
		type: 'GET',
		url: '/account/api/sale',
		dataType: 'json',
		success: function(data, textSTatus, xhr){
			// console.log(data.transaction_ids.length);
			var txids = data.transaction_ids;
			txids.sort();
			load_sale_history_items(txids);
		}
	});
}

$(document).ready(function(){
	xmpp_doConnect();
	// alert("1");
	load_sale_history();
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
		add_sale_div(sale_tx);
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
