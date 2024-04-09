CUDA_VISIBLE_DEVICES=0 nohup python train_model_script/train_bash.py \
    --stage sft \
    --model_name_or_path ./model/origin/Qwen-7B-Chat \
    --do_train True \
    --finetuning_type lora \
    --template qwen \
    --flash_attn False \
    --shift_attn False \
    --dataset_dir data \
    --dataset with_metadata_multi_hop,ner \
    --cutoff_len 1024 \
    --learning_rate 5e-05 \
    --num_train_epochs 3.0 \
    --max_samples 100000 \
    --per_device_train_batch_size 2 \
    --gradient_accumulation_steps 4 \
    --lr_scheduler_type cosine \
    --max_grad_norm 1.0 \
    --logging_steps 5 \
    --save_steps 100 \
    --warmup_steps 0 \
    --neft_alpha 0 \
    --train_on_prompt False \
    --upcast_layernorm False \
    --lora_rank 8 \
    --lora_dropout 0.1 \
    --lora_target c_attn \
    --resume_lora_training False \
    --output_dir ./model/finetune/Qwen-7B-Chat/ \
    --fp16 True \
    --plot_loss True \
    --overwrite_output_dir \
    > train.log 2>&1 &