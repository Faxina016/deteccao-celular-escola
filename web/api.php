<?php
header("Cache-Control: no-cache, must-revalidate");
header('Content-Type: application/json');

$caminhoStatus = __DIR__ . '/status.json';

if (file_exists($caminhoStatus)) {
    $conteudo = file_get_contents($caminhoStatus);
    echo !empty($conteudo) ? $conteudo : json_encode([
        "total_alunos" => 0,
        "alunos_distraidos" => 0,
        "foco_turma" => 100,
        "alertas" => [],
        "ultima_atualizacao" => "Aguardando..."
    ]);
} else {
    echo json_encode([
        "total_alunos" => 0,
        "alunos_distraidos" => 0,
        "foco_turma" => 100,
        "alertas" => [],
        "ultima_atualizacao" => "Sem arquivo status.json"
    ]);
}
?>