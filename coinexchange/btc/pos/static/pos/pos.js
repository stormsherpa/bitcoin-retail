
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

var exchange_rate = 810;

var item_count=1;
$('#test-btn').bind("click", function(){
	var itemhtml = '<div class="span2"><h4>Inserted Item'+ item_count++ +'</h4></div>';
	$('#sale_status_area').prepend(itemhtml);
});

$('#newSaleButton').bind("click", function(){
	$('#newSaleQR').html("");
	$('#newSaleForm')[0].reset();
});

$('#newSaleSubmit').bind("click", function(){
	var sale_form = $($('#newSaleForm')[0]);
	var reference = $(sale_form.find('[name=reference]')[0]).val();
	var currency = $(sale_form.find('[name=currency]')[0]).val();
	var amount = $(sale_form.find('[name=amount]')[0]).val();
	var btc = (amount/exchange_rate).toFixed(8);
	
	var send_address = "1EDuyfcLXwcu7osRtkxGmY6oSRXssy3fHt";
	var qr = qrcode(4, 'M');
	var request_text = 'bitcoin:'+send_address+'?amount='+btc;
	qr.addData(request_text);
	qr.make();
	
	$('#newSaleQR').html(qr.createImgTag(7,5));
	$('#newSaleQR').append('<br/>'+reference+' - '+amount+' '+currency+'<br/>('+btc+' BTC)<br/>'+request_text);
});
