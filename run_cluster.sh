#!/bin/bash

echo "starte alle Nodes..."


ssh node1@139.6.65.29 "./rust_service --config-file input_config.json" &
ssh node2@139.6.65.18 "./rust_service --config-file input_config.json" &
ssh node3@139.6.65.16 "./rust_service --config-file input_config.json" &
ssh node4@139.6.65.25 "./rust_service --config-file input_config.json" &
ssh node5@139.6.65.23 "./rust_service --config-file input_config.json" &
ssh node6@139.6.65.24 "./rust_service --config-file input_config.json" &
ssh node7@139.6.65.26 "./rust_service --config-file input_config.json" &
ssh node8@139.6.65.28 "./rust_service --config-file input_config.json" &

wait
echo "Alle Nodes fertig - sammle Ergebnisse..."


scp node1@139.6.65.29:~/ir_output.json ~/ir_node1.json
scp node2@139.6.65.18:~/ir_output.json ~/ir_node2.json
scp node3@139.6.65.16:~/ir_output.json ~/ir_node3.json
scp node4@139.6.65.25:~/ir_output.json ~/ir_node4.json
scp node5@139.6.65.23:~/ir_output.json ~/ir_node5.json
scp node6@139.6.65.24:~/ir_output.json ~/ir_node5.json
scp node7@139.6.65.26:~/ir_output.json ~/ir_node7.json
scp node8@139.6.65.28:~/ir_output.json ~/ir_node8.json

echo "Alle json eingesammelt!"
