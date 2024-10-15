function atualizarVendas() {
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;

    // Primeira Requisição: Atualizar Vendas
    fetch('/atualizar_vendas', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            'start_date': startDate,
            'end_date': endDate
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "Vendas e transações atualizadas com sucesso") {
            // Segunda Requisição: Ajustar Transações
            return fetch('/ajustar_transacoes');
        } else {
            throw new Error('Erro ao atualizar vendas: ' + data.message);
        }
    })
    .then(response => response.text())
    .then(ajusteResult => {
        if (ajusteResult.includes("sucesso")) {
            alert('Vendas atualizadas e transações ajustadas com sucesso!');
            window.location.reload(); // Recarrega a página para refletir as mudanças
        } else {
            throw new Error('Erro ao ajustar transações: ' + ajusteResult);
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert(error.message || 'Erro na comunicação com o servidor.');
    });
}



function exibirCenterNotification(mensagem) {
    const notification = document.getElementById("center-notification");
    const notificationText = document.getElementById("center-notification-text");
    const overlay = document.getElementById("overlay");

    notificationText.textContent = mensagem;
    notification.style.display = "block";
    overlay.style.display = "block";

    setTimeout(() => {
        notification.style.display = "none";
        overlay.style.display = "none";
    }, 5000);
}