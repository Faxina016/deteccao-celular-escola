<?php
header("Cache-Control: no-cache, must-revalidate");
header('Content-Type: application/json');

$caminhoHistorico = __DIR__ . '/historico.json';

if (file_exists($caminhoHistorico)) {
    $conteudo = file_get_contents($caminhoHistorico);
    echo !empty($conteudo) ? $conteudo : json_encode([]);
} else {
    echo json_encode([]);
}
?>