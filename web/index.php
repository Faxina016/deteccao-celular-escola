<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Monitoramento de Foco Escolar</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; }
        body { background-color: #f0f2f5; color: #1c1e21; padding: 25px; }
        .header { margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 24px; color: #1877f2; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .card { background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); text-align: center; }
        .card h3 { font-size: 13px; color: #65676b; text-transform: uppercase; margin-bottom: 10px; }
        .card .number { font-size: 32px; font-weight: bold; color: #050505; }
        .card.alert { border-bottom: 4px solid #fa383e; }
        .card.success { border-bottom: 4px solid #31a24c; }
        .main-content { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        .chart-box, .list-box, .historico-box { background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .list-box h3, .chart-box h3, .historico-box h3 { font-size: 16px; margin-bottom: 15px; color: #333; }
        ul { list-style: none; }
        li { padding: 12px; border-bottom: 1px solid #f0f2f5; display: flex; justify-content: space-between; align-items: center; }
        .badge { background: #fa383e; color: #fff; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; text-align: left; }
        th, td { padding: 12px; border-bottom: 1px solid #eee; }
        th { background-color: #f8f9fa; color: #555; font-size: 14px; }
    </style>
</head>
<body>

    <div class="header">
        <div>
            <h1>📊 Dashboard de Monitoramento da Sala</h1>
            <p>Acompanhamento de atenção e uso de telefone em tempo real</p>
        </div>
        <div>
            <small>Última atualização: <span id="hora-atualizacao">--:--:--</span></small>
        </div>
    </div>

    <!-- Indicadores -->
    <div class="grid">
        <div class="card">
            <h3>Total de Alunos</h3>
            <div class="number" id="total-alunos">0</div>
        </div>
        <div class="card alert">
            <h3>Usando Celular</h3>
            <div class="number" id="total-distraidos" style="color: #fa383e;">0</div>
        </div>
        <div class="card success">
            <h3>Índice de Foco</h3>
            <div class="number" id="indice-foco" style="color: #31a24c;">100%</div>
        </div>
    </div>

    <!-- Gráficos e Status Atual -->
    <div class="main-content">
        <div class="chart-box">
            <h3>Histórico de Foco da Turma (%)</h3>
            <canvas id="focoChart" height="110"></canvas>
        </div>

        <div class="list-box">
            <h3>🚨 Em Infração Agora</h3>
            <ul id="lista-alertas">
                <li>Aguardando leitura...</li>
            </ul>
        </div>

        <!-- Tabela de Histórico de Registros Guardados -->
        <div class="historico-box" style="grid-column: span 2;">
            <h3>📋 Registro Guardado de Infrações (Uso do Celular)</h3>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Data</th>
                        <th>Hora</th>
                        <th>RA</th>
                        <th>Nome do Aluno</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="tabela-historico">
                    <tr>
                        <td colspan="6" style="text-align: center;">Nenhum registro encontrado.</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('focoChart').getContext('2d');
        const focoChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '% Foco',
                    data: [],
                    borderColor: '#31a24c',
                    backgroundColor: 'rgba(49, 162, 76, 0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: { scales: { y: { min: 0, max: 100 } } }
        });

        // 1. Atualiza dados de tempo real
        async function carregarDados() {
            try {
                const res = await fetch('api.php');
                const data = await res.json();

                document.getElementById('total-alunos').innerText = data.total_alunos;
                document.getElementById('total-distraidos').innerText = data.alunos_distraidos;
                document.getElementById('indice-foco').innerText = data.foco_turma + '%';
                document.getElementById('hora-atualizacao').innerText = data.ultima_atualizacao;

                if (focoChart.data.labels.length > 8) {
                    focoChart.data.labels.shift();
                    focoChart.data.datasets[0].data.shift();
                }
                focoChart.data.labels.push(data.ultima_atualizacao);
                focoChart.data.datasets[0].data.push(data.foco_turma);
                focoChart.update();

                const lista = document.getElementById('lista-alertas');
                lista.innerHTML = '';

                if (!data.alertas || data.alertas.length === 0) {
                    lista.innerHTML = '<li>Nenhum aluno no celular no momento.</li>';
                } else {
                    data.alertas.forEach(a => {
                        lista.innerHTML += `
                            <li>
                                <div>
                                    <strong>${a.nome}</strong><br>
                                    <small style="color: #65676b;">RA: ${a.ra}</small>
                                </div>
                                <span class="badge">${a.status}</span>
                            </li>
                        `;
                    });
                }
            } catch (err) {
                console.error("Erro status:", err);
            }
        }

        // 2. Atualiza a tabela de histórico salvo
        async function carregarHistorico() {
            try {
                const res = await fetch('api_historico.php');
                const historico = await res.json();

                const tabela = document.getElementById('tabela-historico');
                if (!historico || historico.length === 0) {
                    tabela.innerHTML = '<tr><td colspan="6" style="text-align: center;">Nenhuma infração salva até o momento.</td></tr>';
                    return;
                }

                tabela.innerHTML = '';
                historico.forEach(reg => {
                    tabela.innerHTML += `
                        <tr>
                            <td>${reg.id}</td>
                            <td>${reg.data}</td>
                            <td>${reg.hora}</td>
                            <td>${reg.ra}</td>
                            <td><strong>${reg.nome}</strong></td>
                            <td><span class="badge">${reg.status}</span></td>
                        </tr>
                    `;
                });
            } catch (err) {
                console.error("Erro histórico:", err);
            }
        }

        // Loop de atualização
        setInterval(carregarDados, 2000);
        setInterval(carregarHistorico, 4000);
        carregarDados();
        carregarHistorico();
    </script>
</body>
</html>