#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram - CoreQuantik Kelly Calculator v3
Versão de PRODUÇÃO com variável de ambiente
"""

import logging
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CoreQuantikCalculator:
    def __init__(self):
        self.reset()

    def reset(self):
        self.market_type = None
        self.waiting_for_odds = False

    def set_market_type(self, market_type):
        self.market_type = market_type
        self.waiting_for_odds = True
        
        if market_type == "dois_resultados":
            return """
🎯 **Mercado de Dois Resultados selecionado!**

📝 **Digite as odds no formato:**
`OddJusta;OddContrária;OddValor`

**Exemplo:** `1.61;2.31;1.81`
"""
        elif market_type == "sem_juice":
            return """
🎯 **Apostas sem Juice selecionado!**

📝 **Digite as odds no formato:**
`OddJusta;OddValor`

**Exemplo:** `1.51;1.80`
"""
        elif market_type == "com_juice":
            return """
🎯 **Apostas com Juice selecionado!**

📝 **Digite as odds no formato:**
`OddJusta;OddValor`

**Exemplo:** `2.00;2.25`
"""

    def process_odds_input(self, message):
        try:
            # Limpar entrada e dividir por ponto e vírgula
            odds_text = message.replace(" ", "").replace(",", ".")
            odds_parts = odds_text.split(";")
            
            if self.market_type == "dois_resultados":
                if len(odds_parts) != 3:
                    return "❌ **Formato incorreto!**\n\nUse: `OddJusta;OddContrária;OddValor`\nExemplo: `1.61;2.31;1.81`"
                
                fair_odds = float(odds_parts[0])
                opposite_odds = float(odds_parts[1])
                value_odds = float(odds_parts[2])
                
                return self.calculate_two_outcomes(fair_odds, opposite_odds, value_odds)
                
            elif self.market_type in ["sem_juice", "com_juice"]:
                if len(odds_parts) != 2:
                    return "❌ **Formato incorreto!**\n\nUse: `OddJusta;OddValor`\nExemplo: `1.51;1.80`"
                
                fair_odds = float(odds_parts[0])
                value_odds = float(odds_parts[1])
                
                if self.market_type == "sem_juice":
                    return self.calculate_no_juice(fair_odds, value_odds)
                else:
                    return self.calculate_with_juice(fair_odds, value_odds)
                    
        except ValueError:
            return "❌ **Erro nos números!**\n\nVerifique se digitou as odds corretamente.\nUse ponto (.) para decimais."
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            return "❌ Erro no processamento. Tente novamente."

    def calculate_two_outcomes(self, fair_odds, opposite_odds, value_odds):
        try:
            # Calcular probabilidade real removendo juice
            total_implied = (1/fair_odds) + (1/opposite_odds)
            real_prob = (1/fair_odds) / total_implied
            
            # Calcular valor esperado
            expected_value = (value_odds * real_prob) - 1
            
            # Verificar se tem valor
            if expected_value <= 0:
                return "❌ **APOSTA SEM VALOR**\n\nA odd não oferece valor esperado positivo."

            # Calcular Kelly
            kelly_full = expected_value / (value_odds - 1)
            kelly_conservative = kelly_full / 8

            # Aplicar critério de agressividade
            final_stake = self.apply_aggressiveness(kelly_conservative, value_odds)

            # Verificar limite mínimo
            if final_stake < 0.0025:  # 0.25%
                return "❌ **APOSTA SEM VALOR**\n\nStake calculada abaixo do limite mínimo (0.25%)."

            # Converter para porcentagem
            stake_percent = final_stake * 100

            # Resultado final
            result = f"""
📊 **DADOS DE ENTRADA:**
• Odd Justa: {fair_odds}
• Odd Contrária: {opposite_odds}
• Odd de Valor: {value_odds}

🎯 **RECOMENDAÇÃO FINAL:**
💰 **Stake recomendada: {stake_percent:.2f}%**

✅ **APOSTA COM VALOR CONFIRMADA!**

⚠️ *Aposte sempre com responsabilidade!*
"""
            return result.strip()

        except Exception as e:
            logger.error(f"Erro no cálculo dois resultados: {e}")
            return "❌ Erro no cálculo. Tente novamente."

    def calculate_no_juice(self, fair_odds, value_odds):
        try:
            # Probabilidade real (odd já sem juice)
            real_prob = 1 / fair_odds
            
            # Calcular valor esperado
            expected_value = (value_odds * real_prob) - 1
            
            # Verificar se tem valor
            if expected_value <= 0:
                return "❌ **APOSTA SEM VALOR**\n\nA odd não oferece valor esperado positivo."

            # Calcular Kelly
            kelly_full = expected_value / (value_odds - 1)
            kelly_conservative = kelly_full / 8

            # Aplicar critério de agressividade
            final_stake = self.apply_aggressiveness(kelly_conservative, value_odds)

            # Verificar limite mínimo
            if final_stake < 0.0025:  # 0.25%
                return "❌ **APOSTA SEM VALOR**\n\nStake calculada abaixo do limite mínimo (0.25%)."

            # Converter para porcentagem
            stake_percent = final_stake * 100

            # Resultado final
            result = f"""
📊 **DADOS DE ENTRADA:**
• Odd Justa (sem juice): {fair_odds}
• Odd de Valor: {value_odds}

🎯 **RECOMENDAÇÃO FINAL:**
💰 **Stake recomendada: {stake_percent:.2f}%**

✅ **APOSTA COM VALOR CONFIRMADA!**

⚠️ *Aposte sempre com responsabilidade!*
"""
            return result.strip()

        except Exception as e:
            logger.error(f"Erro no cálculo sem juice: {e}")
            return "❌ Erro no cálculo. Tente novamente."

    def calculate_with_juice(self, fair_odds, value_odds):
        try:
            # Adicionar 0.15 para estimar juice
            adjusted_odds = fair_odds + 0.15
            real_prob = 1 / adjusted_odds
            
            # Calcular valor esperado
            expected_value = (value_odds * real_prob) - 1
            
            # Verificar se tem valor
            if expected_value <= 0:
                return "❌ **APOSTA SEM VALOR**\n\nA odd não oferece valor esperado positivo."

            # Calcular Kelly
            kelly_full = expected_value / (value_odds - 1)
            kelly_conservative = kelly_full / 8

            # Aplicar critério de agressividade
            final_stake = self.apply_aggressiveness(kelly_conservative, value_odds)

            # Verificar limite mínimo
            if final_stake < 0.0025:  # 0.25%
                return "❌ **APOSTA SEM VALOR**\n\nStake calculada abaixo do limite mínimo (0.25%)."

            # Converter para porcentagem
            stake_percent = final_stake * 100

            # Resultado final
            result = f"""
📊 **DADOS DE ENTRADA:**
• Odd Justa (com juice): {fair_odds}
• Odd de Valor: {value_odds}

🎯 **RECOMENDAÇÃO FINAL:**
💰 **Stake recomendada: {stake_percent:.2f}%**

✅ **APOSTA COM VALOR CONFIRMADA!**

⚠️ *Aposte sempre com responsabilidade!*
"""
            return result.strip()

        except Exception as e:
            logger.error(f"Erro no cálculo com juice: {e}")
            return "❌ Erro no cálculo. Tente novamente."

    def apply_aggressiveness(self, kelly_conservative, value_odds):
        """Aplicar critério de agressividade baseado na faixa de odds"""
        if 1.01 <= value_odds <= 2.00:
            multiplier = 2.0  # AGRESSIVO
        elif 2.01 <= value_odds <= 3.00:
            multiplier = 1.0  # PADRÃO
        elif 3.01 <= value_odds <= 5.00:
            multiplier = 0.7  # CONSERVADOR
        else:  # 5.01+
            multiplier = 0.5  # MUITO CONSERVADOR

        return kelly_conservative * multiplier

# Dicionário para armazenar calculadoras por usuário
user_calculators = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """
🤖 **CoreQuantik Kelly Calculator v3**

🎯 **Selecione o tipo de mercado:**

Escolha uma das opções abaixo para configurar a calculadora:
"""
    
    keyboard = [
        [InlineKeyboardButton("📊 Mercado de Dois Resultados", callback_data='dois_resultados')],
        [InlineKeyboardButton("🎯 Apostas sem Juice", callback_data='sem_juice')],
        [InlineKeyboardButton("⚡ Apostas com Juice", callback_data='com_juice')],
        [InlineKeyboardButton("❓ Ajuda", callback_data='ajuda')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def ajuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ajuda = """
❓ **Como Usar o CoreQuantik Calculator:**

**1. Selecione o Tipo de Mercado:**
• **Dois Resultados:** Para mercados com contraparte (Ex: Over/Under)
• **Sem Juice:** Quando a odd já está limpa
• **Com Juice:** Quando a odd tem margem da casa

**2. Digite as Odds:**
• **Dois Resultados:** `OddJusta;OddContrária;OddValor`
• **Sem/Com Juice:** `OddJusta;OddValor`

**3. Exemplos:**
• Dois Resultados: `1.61;2.31;1.81`
• Sem Juice: `1.51;1.80`
• Com Juice: `2.00;2.25`

**4. Critérios de Agressividade:**
• **1.01-2.00:** 2x mais agressivo
• **2.01-3.00:** Padrão
• **3.01-5.00:** 0.7x conservador
• **5.01+:** 0.5x muito conservador

⚠️ **Limite mínimo:** 0.25%
"""
    await update.message.reply_text(ajuda, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data in ['dois_resultados', 'sem_juice', 'com_juice']:
        user_calculators[user_id] = CoreQuantikCalculator()
        response = user_calculators[user_id].set_market_type(query.data)
        
        # Adicionar botão para voltar
        keyboard = [[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data='voltar_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(response, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == 'ajuda':
        await ajuda_command(query, context)
    
    elif query.data == 'voltar_menu':
        await start(query, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_calculators:
        await update.message.reply_text(
            "❌ Nenhum mercado selecionado.\n\nDigite /start para escolher um tipo de mercado!",
            parse_mode='Markdown'
        )
        return
    
    calculator = user_calculators[user_id]
    
    if not calculator.waiting_for_odds:
        await update.message.reply_text(
            "❌ Selecione um tipo de mercado primeiro.\n\nDigite /start para começar!",
            parse_mode='Markdown'
        )
        return
    
    response = calculator.process_odds_input(update.message.text)
    
    # Adicionar botões após o resultado
    keyboard = [
        [InlineKeyboardButton("🔄 Nova Análise", callback_data='voltar_menu')],
        [InlineKeyboardButton("❓ Ajuda", callback_data='ajuda')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Reset para nova análise
    calculator.reset()

def main():
    # VALIDAÇÃO ABSOLUTA DO TOKEN PARA PRODUÇÃO
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        print("❌ ERRO CRÍTICO: Variável BOT_TOKEN não encontrada!")
        print("Configure a variável BOT_TOKEN no Railway com seu token real")
        sys.exit(1)
    
    if TOKEN == "SEU_TOKEN_AQUI" or TOKEN == "":
        print("❌ ERRO CRÍTICO: Token inválido!")
        print("Configure o token real na variável BOT_TOKEN do Railway")
        sys.exit(1)
    
    if len(TOKEN) < 40:
        print("❌ ERRO CRÍTICO: Token muito curto!")
        print("Verifique se o token está completo na variável BOT_TOKEN")
        sys.exit(1)
    
    print(f"✅ Token validado: {TOKEN[:15]}...")
    
    # Criar aplicação
    application = Application.builder().token(TOKEN).build()
    
    # Adicionar handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ajuda", ajuda_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Iniciar bot
    print("🤖 Bot Telegram CoreQuantik iniciado!")
    print("📊 Calculadora de Critérios Kelly ativa!")
    print("🔍 Dúvidas perguntar no canal com link na BIO")
    
    application.run_polling()

if __name__ == '__main__':
    main()

