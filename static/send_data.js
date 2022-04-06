window.onload = function () {

    var api_key = document.getElementById('api-key-button');

    var api_secret = document.getElementById('api-secret-button');

    var fee = document.getElementById('fee-button');

    var chat_id = document.getElementById('chat-id-button');

    var tg_token = document.getElementById('token-button');




    api_key.onclick = function() {
        var api_key_input = document.getElementById('input-api').value;
        var password = document.getElementById('input-pass').value;
        send_data('/api_key', api_key_input, password)
    }
    api_secret.onclick = function() {
        var api_secret_input = document.getElementById('input-secret').value;
        var password = document.getElementById('input-pass').value;
        send_data('/api_secret', api_secret_input, password)
    }
    fee.onclick = function() {
        var fee_input = document.getElementById('input-fee').value;
        var password = document.getElementById('input-pass').value;
        send_data('/fee_size', fee_input, password)
    }
    chat_id.onclick = function () {
        var chat_id_input = document.getElementById('input-chat-id').value;
        var password = document.getElementById('input-pass').value;
        send_data('/chat_id', chat_id_input, password)
    }
    tg_token.onclick = function () {
        var tg_token_input = document.getElementById('input-token').value;
        var password = document.getElementById('input-pass').value;
        send_data('/tg_token', tg_token_input, password)
    }

    function send_data(url, input, password) {

        $.ajax({

            url: url,
            method: "POST",
            dataType: 'json',
            data: {'input': input, 'pass': password},
            success: function (data) {
                console.log(data);
            }
        });
}
}
