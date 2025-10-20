57. Configurar ação para
movimento por distância

SZCS#MOVEALMFUN=X

X=0: Automaticamente ativado após entrar no
modo DEFENSE (quando a ignição é desligada)
X=1: Envia um alerta - Apenas uma vez
independente da IGN on ou off
X=2: Envia um alerta uma vez e bloqueia o
veículo - Apenas uma vez independente da IGN
on ou off

Exemplos de Envio:
SZCS#MOVEALMFUN=0
SZCS#MOVEALMFUN=1
SZCS#MOVEALMFUN=2
Exemplos de Resposta:
SETOK: MOVEALMFUN=0
SETOK: MOVEALMFUN=1
SETOK: MOVEALMFUN=2

Request:
CXCS#MOVEALMFUN

Exemplos de Envio:
CXCS#MOVEALMFUN
Exemplos de Resposta:
READOK: MOVEALMFUN=0