import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv('/Users/arturfonseca/PycharmProjects/VendasBanco/.env')

app = Flask(__name__)

# Configuração do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///transacoes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)  # Alterado para DEBUG
logger = logging.getLogger(__name__)

# Modelos
class FormasPagamento(db.Model):
    __tablename__ = 'formas_pagamento'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(100), nullable=False)

class Mentor(db.Model):
    __tablename__ = 'mentor'
    id = db.Column(db.Integer, primary_key=True)
    mentor = db.Column(db.String(100), nullable=False)

class Produtos(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    produto = db.Column(db.String(200), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)
    mentor = db.relationship('Mentor', backref=db.backref('produtos', lazy=True))

class Transacao(db.Model):
    __tablename__ = 'transacao'
    id = db.Column(db.Integer, primary_key=True)
    id_transacao_hotmart = db.Column(db.String(100), nullable=False, unique=True)
    produto = db.Column(db.String(200), nullable=False)
    comprador = db.Column(db.String(200), nullable=False)
    telefone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_aprovacao = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    forma_pagamento = db.Column(db.String(50), nullable=False)

class TransacoesAjustadas(db.Model):
    __tablename__ = 'transacoes_ajustadas'
    id = db.Column(db.Integer, primary_key=True)
    id_transacao_hotmart = db.Column(db.String(100), nullable=False, unique=True)
    produto = db.Column(db.String(200), nullable=False)
    comprador = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_aprovacao = db.Column(db.DateTime, nullable=False)

# Mapeamento de produtos ajustados
PRODUTOS_AJUSTADOS = {
    'imersão evolution julho 2024': 'Imersão Evolution',
    'imersão evolution outubro 2024': 'Imersão Evolution',
    'imersão evolution': 'Imersão Evolution',
    'ls club': 'LS Club',
    'o poder do básico': 'O Poder do Básico',
    'mi liderança': 'MI Liderança',
    'rota do conhecimento - ouro': 'Rota do Conhecimento',
    'rota do conhecimento': 'Rota do Conhecimento',
    'evolution online': 'Evolution Online',
}

# Variáveis globais para o token
access_token = None
token_expiry_time = datetime.utcnow()

def get_new_token():
    global access_token, token_expiry_time
    client_id = os.getenv('HOTMART_CLIENT_ID')
    client_secret = os.getenv('HOTMART_CLIENT_SECRET')
    token_url = 'https://api-sec-vlc.hotmart.com/security/oauth/token'
    data = {
        'grant_type': 'client_credentials',
        'scope': 'read write'  # Verifique se este é o escopo correto
    }

    try:
        logger.debug(f"Solicitando token com dados: {data}")
        response = requests.post(token_url, data=data, auth=(client_id, client_secret))
        logger.debug(f"Resposta da solicitação de token: {response.status_code} {response.text}")
        response.raise_for_status()
        token_data = response.json()
        access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3600)  # padrão 1 hora
        token_expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)
        logger.info(f"Token obtido com sucesso. Expira em {expires_in} segundos.")
        logger.debug(f"Dados do Token: {token_data}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao obter token: {e}")
        if response is not None:
            logger.error(f"Detalhes do erro: {response.text}")
        access_token = None

def obter_token():
    global access_token, token_expiry_time
    if access_token is None or datetime.utcnow() >= token_expiry_time:
        get_new_token()
    return access_token

def to_milliseconds(date_str, end_of_day=False):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        if end_of_day:
            dt = dt + timedelta(days=1) - timedelta(seconds=1)
        return int(dt.timestamp() * 1000)
    except ValueError:
        logger.error("Formato de data inválido. Use AAAA-MM-DD.")
        return None

def from_milliseconds(timestamp):
    return datetime.fromtimestamp(timestamp / 1000)

@app.route('/reset_vendas', methods=['GET'])
def reset_vendas():
    try:
        Transacao.query.delete()
        db.session.commit()
        return "Todas as transações foram excluídas!"
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao tentar resetar vendas: {e}")
        return "Erro ao tentar resetar vendas."
    finally:
        db.session.close()

def buscar_vendas_da_hotmart(start_date=None, end_date=None):
    access_token = obter_token()
    if not access_token:
        logger.error("Erro ao obter o token.")
        return []

    sales_history_url = 'https://developers.hotmart.com/payments/api/v1/sales/history'

    if not start_date:
        start_date = '2024-01-01'
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    # Convert start_date to start of day
    start_date_ms = to_milliseconds(start_date, end_of_day=False)
    # Convert end_date to end of day
    end_date_ms = to_milliseconds(end_date, end_of_day=True)

    if not start_date_ms or not end_date_ms:
        return []

    params = {
        'start_date': str(start_date_ms),
        'end_date': str(end_date_ms),
        'max_results': '100'
    }
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    sales = []
    next_page = True
    page_token = None

    while next_page:
        if page_token:
            params['page_token'] = page_token

        try:
            logger.info(f"Requisição para {sales_history_url} com parâmetros {params}")
            response = requests.get(sales_history_url, headers=headers, params=params)
            logger.debug(f"Resposta da requisição: {response.status_code} {response.text}")
            response.raise_for_status()
            data = response.json()
            sales.extend(data.get('items', []))

            page_info = data.get('page_info', {})
            page_token = page_info.get('next_page_token')
            next_page = bool(page_token)
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro ao obter vendas da Hotmart: {e}")
            if 'response' in locals() and response is not None:
                logger.error(f"Detalhes do erro: {response.text}")
            break

    return sales

def ajustar_transacoes_func():
    transacoes = Transacao.query.all()

    for transacao in transacoes:
        produto_normalizado = transacao.produto.strip().lower()

        produto_ajustado = PRODUTOS_AJUSTADOS.get(produto_normalizado, transacao.produto.strip())

        if TransacoesAjustadas.query.filter_by(id_transacao_hotmart=transacao.id_transacao_hotmart).first():
            logger.info(f"Transação {transacao.id_transacao_hotmart} já existe em TransacoesAjustadas. Ignorando...")
            continue

        nova_transacao_ajustada = TransacoesAjustadas(
            id_transacao_hotmart=transacao.id_transacao_hotmart,
            produto=produto_ajustado,
            comprador=transacao.comprador,
            email=transacao.email,
            valor=transacao.valor,
            data_aprovacao=transacao.data_aprovacao
        )
        db.session.add(nova_transacao_ajustada)

    try:
        db.session.commit()
        logger.info("Transações ajustadas inseridas com sucesso!")
        return "Transações ajustadas inseridas com sucesso!"
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao ajustar transações: {e}")
        return "Erro ao ajustar transações."
    finally:
        db.session.close()

@app.route('/ajustar_transacoes', methods=['GET'])
def ajustar_transacoes():
    result = ajustar_transacoes_func()
    return result

@app.route('/atualizar_vendas', methods=['POST'])
def atualizar_vendas():
    try:
        logger.info("Iniciando a atualização de vendas...")
        start_date = request.form.get('start_date', '2024-01-01')
        end_date = request.form.get('end_date', datetime.now().strftime('%Y-%m-%d'))

        vendas_atualizadas = buscar_vendas_da_hotmart(start_date, end_date)
        logger.info(f"Vendas obtidas da Hotmart: {len(vendas_atualizadas)} registros.")

        for venda in vendas_atualizadas:
            id_transacao_hotmart = venda['purchase'].get('transaction')

            if not id_transacao_hotmart:
                continue

            if Transacao.query.filter_by(id_transacao_hotmart=id_transacao_hotmart).first():
                logger.info(f"Transação com ID {id_transacao_hotmart} já existe. Ignorando...")
                continue

            try:
                nova_venda = Transacao(
                    id_transacao_hotmart=id_transacao_hotmart,
                    produto=venda.get('product', {}).get('name', 'Outro'),
                    comprador=venda['buyer']['name'],
                    telefone=venda['buyer'].get('phone', 'N/A'),
                    email=venda['buyer']['email'],
                    valor=venda['purchase']['price']['value'],
                    data_aprovacao=from_milliseconds(venda['purchase']['approved_date']),
                    status=venda['purchase']['status'],
                    forma_pagamento=venda['purchase']['payment']['method']
                )
                # Formatar valor para exibição no template
                nova_venda.valor_formatado = "R$ {:,.2f}".format(nova_venda.valor).replace(',', 'v').replace('.', ',').replace('v', '.')
                db.session.add(nova_venda)
            except Exception as e:
                logger.error(f"Erro ao processar venda ID {id_transacao_hotmart}: {e}")

        db.session.commit()
        logger.info("Vendas atualizadas com sucesso. Iniciando ajuste de transações.")
        ajuste_result = ajustar_transacoes_func()
        return jsonify({"status": "Vendas e transações atualizadas com sucesso", "ajuste": ajuste_result})
    except Exception as e:
        logger.error(f"Erro ao atualizar vendas: {str(e)}")
        return jsonify({"status": "Erro ao atualizar vendas", "message": str(e)})

@app.route('/transacoes', methods=['GET'])
def listar_transacoes():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    query = TransacoesAjustadas.query

    if start_date:
        try:
            start_date_parsed = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(TransacoesAjustadas.data_aprovacao >= start_date_parsed)
        except ValueError:
            return "Formato de data início inválido. Use AAAA-MM-DD."

    if end_date:
        try:
            end_date_parsed = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(TransacoesAjustadas.data_aprovacao <= end_date_parsed)
        except ValueError:
            return "Formato de data fim inválido. Use AAAA-MM-DD."

    produtos_info = {}

    produtos_ajustados = set(PRODUTOS_AJUSTADOS.values())
    for produto in produtos_ajustados:
        produtos_info[produto] = {'quantidade': 0, 'valor': 0.0}

    total_vendas = 0
    valor_total = 0.0

    # Obter todas as transações filtradas
    transacoes_filtradas = query.order_by(TransacoesAjustadas.data_aprovacao.desc()).all()

    for transacao in transacoes_filtradas:
        produto = transacao.produto
        if produto not in produtos_info:
            produtos_info[produto] = {'quantidade': 0, 'valor': 0.0}
        produtos_info[produto]['quantidade'] += 1
        produtos_info[produto]['valor'] += transacao.valor
        total_vendas += 1
        valor_total += transacao.valor

        # Adiciona a formatação diretamente na transacao
        transacao.valor_formatado = "R$ {:,.2f}".format(transacao.valor).replace(',', 'v').replace('.', ',').replace('v', '.')

    # Formatar valores monetários para produtos_info
    for produto in produtos_info:
        produtos_info[produto]['valor_formatado'] = "R$ {:,.2f}".format(produtos_info[produto]['valor']).replace(',', 'v').replace('.', ',').replace('v', '.')

    valor_total_formatado = "R$ {:,.2f}".format(valor_total).replace(',', 'v').replace('.', ',').replace('v', '.')

    # Paginação
    transacoes_paginadas = query.order_by(TransacoesAjustadas.data_aprovacao.desc()).paginate(page=page, per_page=per_page)

    return render_template('transacoes.html', transacoes=transacoes_paginadas, produtos=produtos_info,
                           total_vendas=total_vendas, valor_total=valor_total_formatado,
                           start_date=start_date, end_date=end_date)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)