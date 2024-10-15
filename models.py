from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class FormasPagamento(db.Model):
    __tablename__ = 'formas_pagamento'  # Nome da tabela
    id = db.Column(db.Integer, primary_key=True)  # ID da forma de pagamento
    codigo = db.Column(db.String(50), unique=True, nullable=False)  # Código da forma de pagamento
    descricao = db.Column(db.String(100), nullable=False)  # Descrição da forma de pagamento

    def __init__(self, codigo, descricao):
        self.codigo = codigo
        self.descricao = descricao


class Mentor(db.Model):
    __tablename__ = 'mentor'  # Nome da tabela
    id = db.Column(db.Integer, primary_key=True)
    mentor = db.Column(db.String(100), nullable=False)

    def __init__(self, mentor):
        self.mentor = mentor


class Produtos(db.Model):
    __tablename__ = 'produtos'  # Nome da tabela
    id = db.Column(db.Integer, primary_key=True)
    produto = db.Column(db.String(200), nullable=False)
    mentor_id = db.Column(db.Integer, db.ForeignKey('mentor.id'), nullable=False)

    mentor = db.relationship('Mentor', backref=db.backref('produtos', lazy=True))

    def __init__(self, produto, mentor_id):
        self.produto = produto
        self.mentor_id = mentor_id


class Transacao(db.Model):
    __tablename__ = 'transacao'  # Nome da tabela
    id = db.Column(db.Integer, primary_key=True)
    id_transacao_hotmart = db.Column(db.String(100), nullable=False)
    produto = db.Column(db.String(200), nullable=False)
    comprador = db.Column(db.String(200), nullable=False)
    telefone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_aprovacao = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    forma_pagamento = db.Column(db.String(50), nullable=False)

    def __init__(self, id_transacao_hotmart, produto, comprador, telefone, email, valor, data_aprovacao, status, forma_pagamento):
        self.id_transacao_hotmart = id_transacao_hotmart
        self.produto = produto
        self.comprador = comprador
        self.telefone = telefone
        self.email = email
        self.valor = valor
        self.data_aprovacao = data_aprovacao
        self.status = status
        self.forma_pagamento = forma_pagamento


class TransacoesAjustadas(db.Model):
    __tablename__ = 'transacoes_ajustadas'  # Nome da tabela no banco de dados
    id = db.Column(db.Integer, primary_key=True)  # ID
    id_transacao_hotmart = db.Column(db.String(100), nullable=False)  # ID da transação Hotmart
    produto = db.Column(db.String(200), nullable=False)  # Nome do produto ajustado
    comprador = db.Column(db.String(200), nullable=False)  # Nome do comprador
    email = db.Column(db.String(150), nullable=False)  # Email do comprador
    valor = db.Column(db.Float, nullable=False)  # Valor da transação
    data_aprovacao = db.Column(db.DateTime, nullable=False)  # Data da aprovação

    def __init__(self, id_transacao_hotmart, produto, comprador, email, valor, data_aprovacao):
        self.id_transacao_hotmart = id_transacao_hotmart
        self.produto = produto
        self.comprador = comprador
        self.email = email
        self.valor = valor
        self.data_aprovacao = data_aprovacao