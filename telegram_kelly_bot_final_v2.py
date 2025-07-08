#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Telegram - Calculadora de Kelly
Versão Final v2 com Critério de Agressividade - COMPLETAMENTE LIMPO
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

class KellyCalculator:
    def __init__(self):
        self.reset()

    def reset(self):
        self.step = 'start'
        self.has_opposite_market = None
        self.is_juice_free = None
        self.fair_odds = None
        self.opposite_odds = None
        self.value_odds = None

    def start_conversation(self):
        self.step = 'opposite_market'
        return "❓ **O mercado que deseja apostar tem mercado contrário?**"

    def process_message(self, message):
        response = message.lower().strip()

        if self.step == 'opposite_market':
            if response in ['sim', 's', 'yes', 'y']:
                self.has_opposite_market = True
                self.step = 'fair_odds'
                return "📊 **Qual a odd justa?** (Ex: 1.66)"
            elif response in ['não', 'nao', 'n', 'no']:
                self.has_opposite_market = False
                self.step = 'juice_question'
                return "🔍 **A odd de referência já está sem juice?**"
            else:
                return "❌ Por favor, responda 'Sim' ou 'Não'"

        elif self.step == 'juice_question':
            if response in ['sim', 's', 'yes', 'y']:
                self.is_juice_free = True
                self.step = 'fair_odds'
                return "📊 **Qual a odd de referência (sem juice)?** (Ex: 2.38)"
            elif response in ['não', 'nao', 'n', 'no']:
                self.is_juice_free = False
                self.step = 'fair_odds'
                return "📊 **Qual a odd justa?** (Ex: 2.00)"
            else:
                return "❌ Por favor, responda 'Sim' ou 'Não'"

        elif self.step == 'fair_odds':
            try:
                self.fair_odds = float(response.replace(',', '.'))
                if self.fair_odds <= 1.0:
                    return "❌ A odd deve ser maior que 1.0"
                
                if self.has_opposite_market:
                    self.step = 'opposite_odds'
                    return "📈 **Qual a odd do mercado contrário?** (Ex: 2.20)"
                else:
                    self.step = 'value_odds'
                    return "💰 **Qual a odd de valor encontrada?** (Ex: 2.65)"
            except ValueError:
                return "❌ Por favor, digite um número válido (Ex: 1.66)"

        elif self.step == 'opposite_odds':
            try:
                self.opposite_odds = float(response.replace(',', '.'))
                if self.opposite_odds <= 1.0:
                    return "❌ A odd deve ser maior que 1.0"
                
                self.step = 'value_odds'
                return "💰 **Qual a odd de valor encontrada?** (Ex: 2.50)"
            except ValueError:
                return "❌ Por favor, digite um número válido (Ex: 2.20)"

        elif self.step == 'value_odds':
            try:
                self.value_odds = float(response.replace(',', '.'))
                if self.value_odds <= 1.0:
                    return "❌ A odd deve ser maior que 1.0"
                
                return self.calculate_kelly()
            except ValueError:
                return "❌ Por favor, digite um número válido (Ex: 2.50)"

        return "❌ Erro no processamento. Digite /calcular para recomeçar."

    def calculate_kelly(self):
        try:
            if self.has_opposite_market:
                # Calcular probabilidade real removendo juice
                total_implied = (1/self.fair_odds) + (1/self.opposite_odds)
                real_prob = (1/self.fair_odds) / total_implied
            else:
                # Sem mercado contrário
                if self.is_juice_free:
                    # Odd já está sem juice
                    real_prob = 1 / self.fair_odds
                else:
                    # Adicionar 0.15 para estimar juice
                    adjusted_odds = self.fair_odds + 0.15
                    real_prob = 1 / adjusted_odds

            # Calcular valor esperado
            expected_value = (self.value_odds * real_prob) - 1
            
            # Verificar se tem valor
            if expected_value <= 0:
                return "❌ **APOSTA SEM VALOR**\n\nA odd não oferece valor esperado positivo."

            # Calcular Kelly
            kelly_full = expected_value / (self.value_odds - 1)
            kelly_conservative = kelly_full / 8

            # CRITÉRIO DE AGRESSIVIDADE POR FAIXA DE ODDS
            if 1.01 <= self.value_odds <= 2.00:
                multiplier = 2.0
                risk_profile = "🔥 AGRESSIVO"
            elif 2.01 <= self.value_odds <= 3.00:
                multiplier = 1.0
                risk_profile = "⚖️ PADRÃO"
            elif 3.01 <= self.value_odds <= 5.00:
                multiplier = 0.7
                risk_profile = "🛡️ CONSERVADOR"
            else:  # 5.01+
                multiplier = 0.5
                risk_profile = "🔒 MUITO CONSERVADOR"

            # Aplicar multiplicador de agressividade
            final_stake = kelly_conservative * multiplier

            # Verificar limite mínimo
            if final_stake < 0.0025:  # 0.25%
                return "❌ **APOSTA SEM VALOR**\n\nStake calculada abaixo do limite mínimo (0.25%)."

            # Converter para porcentagem
            stake_percent = final_stake * 100

            # Preparar dados de entrada
            if self.has_opposite_market:
                input_data = f"📊 **Odd Justa:** {self.fair_odds}\n📈 **Odd Contrária:** {self.opposite_odds}\n💰 **Odd de Valor:** {self.value_odds}"
            else:
                juice_status = "sem juice" if self.is_juice_free else "com juice"
                input_data = f"📊 **Odd de Referência ({juice_status}):** {self.fair_odds}\n💰 **Odd de Valor:** {self.value_odds}"

            # Resultado final
            result = f"""
{input_data}

🎯 **RECOMENDAÇÃO FINAL:**

**STAKE RECOMENDADA: {stake_percent:.2f}%**

✅ **APOSTA COM VALOR CONFIRMADA!**

⚠️ *Aposte com responsabilidade. Esta é apenas uma sugestão matemática.*
"""
            return result.strip()

        except Exception as e:
            logger.error(f"Erro no cálculo: {e}")
            return "❌ Erro no cálculo. Tente novamente."

# Dicionário para armazenar calculadoras por usuário
user_calculators = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """
🤖 **Calculadora de Kelly v2 - Bot Telegram**

🎯 **Funcionalidades:**
• Cálculo de Kelly conservador (1/8)
• Critério de agressividade por faixa de odds
• Suporte a mercados com e sem contraparte
• Detecção automática de juice

🔥 **Critérios de Agressividade:**
• 1.01-2.00: 2x mais agressivo
• 2.01-3.00: Padrão
• 3.01-5.00: 0.7x conservador
• 5.01+: 0.5x muito conservador

📊 **Comandos:**
/calcular - Iniciar cálculo
/exemplo - Ver exemplo prático
/ajuda - Ajuda detalhada

⚠️ *Use com responsabilidade. Aposte apenas o que pode perder.*
"""
    
    keyboard = [
        [InlineKeyboardButton("🧮 Calcular Kelly", callback_data='calcular')],
        [InlineKeyboardButton("📊 Ver Exemplo", callback_data='exemplo')],
        [InlineKeyboardButton("❓ Ajuda", callback_data='ajuda')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def calcular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_calculators[user_id] = KellyCalculator()
    
    response = user_calculators[user_id].start_conversation()
    await update.message.reply_text(response, parse_mode='Markdown')

async def exemplo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    exemplo = """
📊 **Exemplo Prático - Critério de Agressividade:**

**Cenário 1: Odd Baixa (Agressivo)**
• Odd Justa: 1.61
• Odd de Valor: 1.81
• Stake Base: 1.01%
• **Com Agressividade (2x): 2.02%** 🔥

**Cenário 2: Odd Média (Padrão)**
• Odd Justa: 2.38 (sem juice)
• Odd de Valor: 2.65
• **Stake Recomendada: 0.86%** ⚖️

**Cenário 3: Odd Alta (Conservador)**
• Odd Justa: 4.50
• Odd de Valor: 5.20
• Stake Base: 1.20%
• **Com Conservadorismo (0.7x): 0.84%** 🛡️

Digite /calcular para fazer seu próprio cálculo!
"""
    await update.message.reply_text(exemplo, parse_mode='Markdown')

async def ajuda_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ajuda = """
❓ **Como Usar a Calculadora:**

**1. Mercado Contrário:**
• Responda se existe mercado oposto (Ex: Over/Under)

**2. Juice na Odd:**
• Se não há mercado contrário, informe se a odd já está "limpa"

**3. Digite as Odds:**
• Odd justa/referência
• Odd contrária (se houver)
• Odd de valor encontrada

**4. Receba a Recomendação:**
• Stake calculada com Kelly conservador
• Ajustada pelo critério de agressividade

🎯 **Critérios de Agressividade:**
• **Odds 1.01-2.00:** 2x (alta probabilidade)
• **Odds 2.01-3.00:** 1x (padrão)
• **Odds 3.01-5.00:** 0.7x (conservador)
• **Odds 5.01+:** 0.5x (muito conservador)

⚠️ **Importante:**
• Limite mínimo: 0.25%
• Aposte com responsabilidade
• Esta é apenas uma sugestão matemática
"""
    await update.message.reply_text(ajuda, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'calcular':
        user_id = query.from_user.id
        user_calculators[user_id] = KellyCalculator()
        response = user_calculators[user_id].start_conversation()
        await query.edit_message_text(response, parse_mode='Markdown')
    
    elif query.data == 'exemplo':
        await exemplo_command(query, context)
    
    elif query.data == 'ajuda':
        await ajuda_command(query, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_calculators:
        await update.message.reply_text(
            "❌ Nenhum cálculo em andamento.\n\nDigite /calcular para iniciar!",
            parse_mode='Markdown'
        )
        return
    
    calculator = user_calculators[user_id]
    response = calculator.process_message(update.message.text)
    
    # Se o cálculo foi finalizado, adicionar botões
    if "STAKE RECOMENDADA" in response or "APOSTA SEM VALOR" in response:
        keyboard = [
            [InlineKeyboardButton("🔄 Nova Análise", callback_data='calcular')],
            [InlineKeyboardButton("📊 Ver Exemplo", callback_data='exemplo')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(response, reply_markup=reply_markup, parse_mode='Markdown')
        del user_calculators[user_id]
    else:
        await update.message.reply_text(response, parse_mode='Markdown')

def main():
    # VALIDAÇÃO ABSOLUTA DO TOKEN
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
    application.add_handler(CommandHandler("calcular", calcular_command))
    application.add_handler(CommandHandler("exemplo", exemplo_command))
    application.add_handler(CommandHandler("ajuda", ajuda_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Iniciar bot
    print("🤖 Bot Telegram iniciado com sucesso!")
    print("📊 Calculadora de Kelly v2 com Agressividade ativa!")
    print("🔍 Limite mínimo: 0.25%")
    print("🎯 Critério de agressividade implementado!")
    print("🔥 Multiplicadores: 2x, 1x, 0.7x, 0.5x")
    
    application.run_polling()

if __name__ == '__main__':
    main()

