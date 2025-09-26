import uuid
import json
import random
import mimetypes
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q, Max, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.clickjacking import xframe_options_exempt

from .forms import EventoForm
from .models import (
    ChatRoom,
    Usuario,
    SolicitacaoClube,
    Mensagem,
    Conversation,
    Recado,
    Clube,
    Topico,
    Resposta,
    Sala,
    SalaMensagem,
    Evento,
    Post,
    Tema,
    Novidade,
    WPlaceState,
)

# Usuario = get_user_model()

waiting_users = []  
active_rooms = {}

def home(request):
    session_key = request.session.session_key
    usuario_logado = Usuario.objects.filter(session_key=session_key).first()

    if not usuario_logado:
        return render(request, 'chat/home.html', {'usuarios': Usuario.objects.all()})

    clubes_seguidos = usuario_logado.clubes_seguidos.all() if hasattr(usuario_logado, 'clubes_seguidos') else []
    feed_posts = Post.objects.filter(clube__in=clubes_seguidos).order_by('-data')[:10]

    recados = Recado.objects.all().order_by('-data')[:10]

    perfil_destaque = Usuario.objects.exclude(id=usuario_logado.id).order_by('?').first()
    tema_semana = Tema.objects.filter(ativo=True).first()
    evento_destaque = "Noite Lo-fi no Café Virtual"

    clubes_recomendados = Clube.objects.exclude(id__in=[c.id for c in clubes_seguidos])[:5]

    perfis_recomendados = Usuario.objects.exclude(id=usuario_logado.id).annotate(
        afinidade=Count('gostos')
    ).order_by('-afinidade')[:5]

    novidades = Novidade.objects.order_by('-data')[:5]

    usuarios = Usuario.objects.all().order_by('nome')

    return render(request, 'chat/home.html', {
        "usuario_logado": usuario_logado,
        "feed_posts": feed_posts,
        "recados": recados,
        "perfil_destaque": perfil_destaque,
        "tema_semana": tema_semana,
        "evento_destaque": evento_destaque,
        "clubes_recomendados": clubes_recomendados,
        "perfis_recomendados": perfis_recomendados,
        "novidades": novidades,
        "usuarios": usuarios
    })




def get_session_id(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key

def chat(request):
    session_key = get_session_id(request)

    if not session_key:
        return render(request, 'chat/waiting.html', {'error': 'Habilite os cookies.'})

    room_id = active_rooms.get(session_key)
    if room_id:
        room = ChatRoom.objects.filter(id=room_id).first()
        if room and session_key in (room.user1, room.user2):
            return redirect('chat:chat_view', room_id=room_id)
        else:
            active_rooms.pop(session_key, None)

    return render(request, 'chat/waiting.html')

def chat_view(request, room_id):
    session_key = get_session_id(request)
    room = ChatRoom.objects.filter(id=room_id).first()

    if not room or session_key not in (room.user1, room.user2):
        request.session.pop('room_id', None)
        return redirect('chat:chat')

    request.session['room_id'] = room_id

    usuario_logado = Usuario.objects.filter(id=request.session.get('usuario_id')).first()
    if usuario_logado and usuario_logado.session_key != session_key:
        usuario_logado.session_key = session_key
        usuario_logado.save()

    partner_session_key = room.user2 if session_key == room.user1 else room.user1
    partner_user = Usuario.objects.filter(session_key=partner_session_key).first()

    return render(request, 'chat/chat.html', {
        'room': room,
        'partner_user': partner_user,
        'usuario_logado': usuario_logado,
    })

def leave_chat(request):
    session_key = get_session_id(request)

    global waiting_users, active_rooms
    waiting_users = [w for w in waiting_users if w['session_key'] != session_key]

    room_id = request.session.get('room_id')
    if room_id:
        active_rooms.pop(session_key, None)
        request.session.pop('room_id', None)

    return redirect('/')



# Variáveis globais simulando fila e salas ativas
waiting_users = []
active_rooms = {}

def normalize_gostos(gostos_raw):
    if not gostos_raw:
        return []
    if isinstance(gostos_raw, list):
        return [str(g).strip().lower() for g in gostos_raw if str(g).strip()]
    if isinstance(gostos_raw, str):
        try:
            parsed = json.loads(gostos_raw)
            if isinstance(parsed, list):
                return [str(g).strip().lower() for g in parsed if str(g).strip()]
        except Exception:
            return [g.strip().lower() for g in gostos_raw.split(",") if g.strip()]
    return [str(gostos_raw).strip().lower()]

@csrf_exempt
def find_match(request):
    global waiting_users, active_rooms

    if request.method != 'POST':
        return JsonResponse({'error': 'Use POST'}, status=405)

    data = json.loads(request.body)
    use_temp_interests = data.get('use_temp_interests', False)
    temp_interests_raw = data.get('temp_interests_raw', '')

    session_key = request.session.session_key
    if not session_key:
        return JsonResponse({'error': 'Sem session_key'}, status=400)

    usuario = Usuario.objects.filter(session_key=session_key).first()
    if not usuario:
        return JsonResponse({'error': 'Usuário não encontrado'}, status=400)

    temp_interests = [g.strip().lower() for g in temp_interests_raw.split(",") if g.strip()] if use_temp_interests else []

    # Se já está em sala ativa, retorna imediatamente
    if session_key in active_rooms:
        return JsonResponse({'room_id': active_rooms[session_key]})

    # Adiciona o usuário na fila se não estiver
    if not any(w['session_key'] == session_key for w in waiting_users):
        waiting_users.append({
            'session_key': session_key,
            'temp_interests': temp_interests
        })

    # Filtra usuários na fila, exceto ele mesmo
    waiting_usuarios = [w for w in waiting_users if w['session_key'] != session_key]

    # Se nenhum parceiro disponível
    if not waiting_usuarios:
        return JsonResponse({'room_id': None})

    user_gostos = normalize_gostos(usuario.gostos)

    parceiros_validos = []
    for w in waiting_usuarios:
        partner_user = Usuario.objects.filter(session_key=w['session_key']).first()
        if not partner_user:
            continue

        # Ignora se bloqueado
        if usuario.esta_bloqueado(partner_user):
            continue

        partner_gostos = normalize_gostos(partner_user.gostos)

        # Verifica gostos temporários se aplicável
        if use_temp_interests and temp_interests:
            comum_temp = set(temp_interests) & set(w.get('temp_interests', []))
            if not comum_temp:
                continue

        # Verifica gostos fixos do usuário
        if user_gostos and partner_gostos:
            comum_gostos = set(user_gostos) & set(partner_gostos)
            if not comum_gostos:
                continue

        # Verifica localização igual se definida (não obrigatório, só exemplo)
        if usuario.localizacao and partner_user.localizacao:
            if usuario.localizacao.strip().lower() != partner_user.localizacao.strip().lower():
                # Para aceitar somente mesmo local, descomente a linha abaixo
                # continue
                pass

        parceiros_validos.append(partner_user)

    if not parceiros_validos:
        return JsonResponse({'room_id': None})

    partner_user = parceiros_validos[0]

    new_room_id = str(uuid.uuid4())[:8]
    ChatRoom.objects.create(id=new_room_id, user1=usuario.session_key, user2=partner_user.session_key)

    active_rooms[usuario.session_key] = new_room_id
    active_rooms[partner_user.session_key] = new_room_id

    # Remove ambos da fila
    waiting_users = [
        w for w in waiting_users
        if w['session_key'] not in (usuario.session_key, partner_user.session_key)
    ]

    return JsonResponse({'room_id': new_room_id})


def clubes(request):
    return render(request, 'chat/clubes.html')  # ajuste o caminho se for necessário



def profile(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('chat:login')

    usuario = Usuario.objects.get(id=usuario_id)

    # Atualiza o contador de acessos consecutivos
    usuario.registrar_acesso()

    # Passa os clubes do usuário para o template
    clubes = usuario.clubes.all()

    recados = Recado.objects.filter(perfil=usuario).order_by('-data')

    return render(request, 'chat/profile.htm', {
        'usuario': usuario,
        'usuario_logado': usuario,  # para compatibilidade com outros templates
        'clubes': clubes,
        'recados': recados,
    })





def editar_perfil_view(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('chat:login')  # Ou onde quiser

    usuario = Usuario.objects.get(id=usuario_id)
    
    # Passe os dados do usuário para popular o formulário
    context = {
        'usuario': usuario,
    }
    return render(request, 'chat/edit.html', context)




@csrf_exempt
def editar_perfil(request):
    if request.method == 'POST':
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            return JsonResponse({'erro': 'Não autenticado'}, status=401)

        data = json.loads(request.body)
        usuario = Usuario.objects.get(id=usuario_id)

        usuario.foto = data.get('pic')
        usuario.emoji = data.get('emotion')
        usuario.nome = data.get('name')
        usuario.descricao = data.get('description')
        usuario.localizacao = data.get('location')
        usuario.gostos = data.get('likes', [])
        usuario.redes_sociais = data.get('socials', [])
        usuario.playlist = data.get('playlistUrl')

        usuario.save()
        return JsonResponse({'sucesso': True})

    return JsonResponse({'erro': 'Método inválido'}, status=400)




def register(request):
    if request.method == 'POST':
        nome = request.POST['nome']
        email = request.POST['email']
        senha = request.POST['senha']

        if Usuario.objects.filter(email=email).exists():
            messages.error(request, "E-mail já cadastrado.")
            return redirect('chat:register')

        token = f"{random.randint(100000, 999999)}"
        expiracao = (timezone.now() + timedelta(hours=1)).isoformat()

        request.session['registro_temp'] = {
            'nome': nome,
            'email': email,
            'senha': senha,
            'token': token,
            'expiracao': expiracao,
        }

        send_mail(
            'Confirmação de Cadastro',
            f'Olá, {nome}! Seu token de 6 dígitos é:\n\n{token}\n\nExpira em 1 hora.',
            settings.EMAIL_HOST_USER,
            [email]
        )

        return redirect('chat:confirm_token')

    return render(request, 'chat/register.html')



def confirm_token(request):
    registro = request.session.get('registro_temp')

    if not registro:
        messages.error(request, "Sessão expirada. Registre-se novamente.")
        return redirect('chat:register')

    if request.method == 'POST':
        token_digitado = request.POST.get('token')
        token_correto = registro['token']
        expiracao = timezone.datetime.fromisoformat(registro['expiracao'])

        if token_digitado != token_correto:
            messages.error(request, "Token inválido.")
            return render(request, 'chat/confirm_token.html')

        if timezone.now() > expiracao:
            messages.error(request, "Token expirado. Registre-se novamente.")
            del request.session['registro_temp']
            return redirect('chat:register')

        # Criar o usuário agora que o token foi validado
        Usuario.objects.create(
            nome=registro['nome'],
            email=registro['email'],
            senha=registro['senha']
        )

        # Limpa a sessão
        del request.session['registro_temp']

        messages.success(request, "Cadastro confirmado com sucesso.")
        return redirect('chat:login')

    return render(request, 'chat/confirm_token.html')



def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('username')
        senha = request.POST.get('password')

        usuario = Usuario.objects.filter(email=email).first()

        if usuario:
            if usuario.senha == senha:
                # Garante que a sessão está criada
                if not request.session.session_key:
                    request.session.save()
                session_key = request.session.session_key

                # Salva o ID na sessão
                request.session['usuario_id'] = usuario.id

                # Salva a session_key no banco
                usuario.session_key = session_key
                usuario.save()

                # Adiciona o mapeamento session_key → usuario.id
                usuario_id_map = request.session.get('usuario_id_map', {})
                usuario_id_map[session_key] = usuario.id
                request.session['usuario_id_map'] = usuario_id_map

                return redirect('chat:profile')
            else:
                messages.error(request, "Senha incorreta.")
        else:
            messages.error(request, "Email não encontrado.")

    return render(request, 'chat/login.html')


















def adicionar_amigo(request, usuario_id):
    if request.method == 'POST':
        logado_id = request.session.get('usuario_id')
        if not logado_id:
            return redirect('chat:login')

        logado = get_object_or_404(Usuario, id=logado_id)
        amigo = get_object_or_404(Usuario, id=usuario_id)

        if amigo in logado.amigos.all():
            logado.amigos.remove(amigo)  # remover amizade
        else:
            logado.amigos.add(amigo)  # adicionar amizade

        return redirect('chat:perfil_usuario', usuario_id=usuario_id)




def get_usuario_logado(request):
    uid = request.session.get('usuario_id')
    return get_object_or_404(Usuario, id=uid)

def perfil_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, id=usuario_id)
    usuario_logado = get_usuario_logado(request)

    # Bloqueio: se o usuário logado está bloqueado pelo dono do perfil, bloqueie o acesso
    if usuario_logado in usuario.bloqueados.all():
        return HttpResponseForbidden("Você foi bloqueado por este usuário e não pode acessar o perfil.")

    # Opcional: se quiser evitar que alguém veja o próprio perfil via essa view (depende da sua lógica)
    if usuario_logado == usuario:
        # Pode redirecionar para a própria página de perfil privada ou apenas permitir
        pass

    # cria ou recupera a conversation
    conv = Conversation.get_or_create_conversation(usuario_logado, usuario)

    # busca recados e adiciona posições aleatórias
    recados = Recado.objects.filter(perfil=usuario).order_by('-data')
    
    return render(request, 'chat/profile_publico.html', {
        'usuario': usuario,
        'ja_amigo': usuario in usuario_logado.amigos.all(),
        'conv_id': conv.id,
        'recados': recados,
        'usuario_logado': usuario_logado
    })




@csrf_exempt
@require_POST
def enviar_recado(request, usuario_id):
    try:
        perfil = get_object_or_404(Usuario, id=usuario_id)
        usuario_logado = get_object_or_404(Usuario, id=request.session.get('usuario_id'))

        data = json.loads(request.body)
        texto = data.get('texto', '').strip()
        reacoes = data.get('reacoes', '').strip()
        foto = data.get('foto') or usuario_logado.foto or 'https://i.pravatar.cc/44'
        left = int(data.get('left', random.randint(10, 280)))
        top = int(data.get('top', random.randint(60, 160)))

        if not texto:
            return JsonResponse({'status': 'erro', 'msg': 'Texto vazio'}, status=400)

        recado = Recado.objects.create(
            perfil=perfil,
            autor=usuario_logado.nome,
            foto=foto,
            texto=texto,
            reacoes=reacoes,
            left=left,
            top=top
        )

        return JsonResponse({
            'status': 'ok',
            'recado': {
                'id': recado.id,
                'autor': recado.autor,
                'foto': recado.foto,
                'texto': recado.texto,
                'reacoes': recado.reacoes,
                'data': recado.data.strftime('%d/%m'),
                'left': recado.left,
                'top': recado.top
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'erro', 'msg': str(e)}, status=500)



def conversation_view(request, conv_id):
    conv = get_object_or_404(Conversation, id=conv_id)
    usuario_logado = get_usuario_logado(request)

    if usuario_logado not in (conv.user1, conv.user2):
        return redirect('chat:home')

    mensagens = Mensagem.objects.filter(conversation=conv).order_by('timestamp')

    # Marcar como "vistas"
    for msg in mensagens:
        if msg.remetente != usuario_logado and not msg.visto_por.filter(id=usuario_logado.id).exists():
            msg.visto_por.add(usuario_logado)

    amigo = conv.user2 if usuario_logado == conv.user1 else conv.user1

    return render(request, 'chat/conversation.html', {
        'conv_id': conv.id,
        'amigo': amigo,
        'mensagens': mensagens,
    })


@csrf_exempt
@require_POST
def send_conversation_message(request, conv_id):
    conv = get_object_or_404(Conversation, id=conv_id)
    usuario = get_usuario_logado(request)

    if usuario not in (conv.user1, conv.user2):
        return JsonResponse({'status': 'erro', 'msg': 'Não autorizado'}, status=403)

    destinatario = conv.user2 if usuario == conv.user1 else conv.user1

    ctype = request.META.get('CONTENT_TYPE', '')
    conteudo = ''
    audio = None
    midia = None

    if 'application/json' in ctype:
        try:
            payload = json.loads(request.body.decode('utf-8'))
            conteudo = payload.get('conteudo', '').strip()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'status': 'erro', 'msg': 'JSON inválido'}, status=400)
    else:
        conteudo = request.POST.get('conteudo', '').strip()
        audio = request.FILES.get('audio')
        midia = request.FILES.get('midia')

    if not any([conteudo, audio, midia]):
        return JsonResponse({'status': 'erro', 'msg': 'Nada para enviar'}, status=400)

    Mensagem.objects.create(
        conversation=conv,
        remetente=usuario,
        destinatario=destinatario,
        conteudo=conteudo,
        audio=audio,
        midia=midia
    )

    return JsonResponse({'status': 'ok'})


def conversation_messages_json(request, conv_id):
    conv = get_object_or_404(Conversation, id=conv_id)
    usuario_logado = get_usuario_logado(request)

    if usuario_logado not in (conv.user1, conv.user2):
        return JsonResponse({'status': 'erro', 'msg': 'Não autorizado'}, status=403)

    mensagens = Mensagem.objects.filter(conversation=conv).order_by('timestamp')
    resultado = []

    for m in mensagens:
        midia_url = m.midia.url if m.midia else None
        midia_tipo = None
        if m.midia:
            mimetype, _ = mimetypes.guess_type(m.midia.url)
            if mimetype:
                if mimetype.startswith('image'):
                    midia_tipo = 'imagem'
                elif mimetype.startswith('video'):
                    midia_tipo = 'video'
                elif mimetype.startswith('application'):
                    midia_tipo = 'documento'
                else:
                    midia_tipo = 'outro'

        resultado.append({
            'id': m.id,
            'remetente': m.remetente.nome,
            'remetente_id': m.remetente.id,
            'conteudo': m.conteudo,
            'audio_url': m.audio.url if m.audio else None,
            'midia_url': midia_url,
            'midia_tipo': midia_tipo,
            'midia_nome': m.midia.name.split('/')[-1] if m.midia else '',
            'timestamp': m.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        })

    return JsonResponse({'mensagens': resultado})


@csrf_exempt
@require_POST
def enviar_mensagem(request, conv_id):
    conv = get_object_or_404(Conversation, id=conv_id)
    usuario_logado = get_usuario_logado(request)
    destinatario = conv.user2 if usuario_logado == conv.user1 else conv.user1

    # aceita multipart/form-data ou JSON
    audio = request.FILES.get('audio')
    midia = request.FILES.get('midia')
    texto = request.POST.get('conteudo', '').strip() if request.method == 'POST' else ''

    if not texto and not audio and not midia:
        return JsonResponse({'status': 'erro', 'msg': 'Nada enviado'}, status=400)

    Mensagem.objects.create(
        conversation=conv,
        remetente=usuario_logado,
        destinatario=destinatario,
        conteudo=texto,
        audio=audio,
        midia=midia
    )
    return JsonResponse({'status': 'ok'})





@csrf_exempt
@require_POST
def mover_recado(request, recado_id):
    try:
        data = json.loads(request.body)
        left = int(data.get('left', 0))
        top = int(data.get('top', 0))
        z_index = data.get('z_index')  # pode vir como None

        print(f"Movendo recado {recado_id} para left={left}, top={top}, z_index={z_index}")

        recado = get_object_or_404(Recado, id=recado_id)
        recado.left = left
        recado.top = top
        if z_index is not None:
            recado.z_index = int(z_index)
        recado.save()

        return JsonResponse({'status': 'ok'})
    except Exception as e:
        print(f"Erro ao mover recado: {e}")
        return JsonResponse({'status': 'erro', 'detalhe': str(e)}, status=400)

@csrf_exempt
@require_POST
def excluir_recado(request, recado_id):
    try:
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            return JsonResponse({'status': 'erro', 'msg': 'Não autenticado'}, status=401)

        usuario_logado = get_object_or_404(Usuario, id=usuario_id)
        recado = get_object_or_404(Recado, id=recado_id)

        if recado.autor != usuario_logado.nome:
            return JsonResponse({'status': 'erro', 'msg': 'Não autorizado'}, status=403)

        recado.delete()
        return JsonResponse({'status': 'ok'})

    except Exception as e:
        return JsonResponse({'status': 'erro', 'msg': str(e)}, status=500)



@csrf_exempt
@require_POST
def excluir_recado_usuario(request, recado_id):
    try:
        usuario_id = request.session.get('usuario_id')
        if not usuario_id:
            return JsonResponse({'status': 'erro', 'msg': 'Não autenticado'}, status=401)

        # Só garante que o usuário existe, mas não bloqueia exclusão
        usuario_logado = get_object_or_404(Usuario, id=usuario_id)

        recado = get_object_or_404(Recado, id=recado_id)
        recado.delete()

        return JsonResponse({'status': 'ok'})

    except Exception as e:
        return JsonResponse({'status': 'erro', 'msg': str(e)}, status=500)






# Formulário de criação e edição de clubes
class ClubeForm(forms.ModelForm):
    class Meta:
        model = Clube
        fields = ['nome', 'imagem', 'idioma', 'categoria', 'tipo', 'data', 'dono', 'mods', 'descricao']


def clubes_lista(request):
    clubes = Clube.objects.all().order_by('nome')
    return render(request, 'chat/clubes_lista.html', {'clubes': clubes})




def clubes_detalhe(request, pk):
    clube = get_object_or_404(Clube, pk=pk)
    usuario_id = request.session.get('usuario_id')
    usuario_logado = Usuario.objects.filter(id=usuario_id).first()
    membros = Usuario.objects.filter(clubes=clube)

    mods_list = [mod.strip() for mod in clube.mods.split(',')] if clube.mods else []
    usuario_no_clube = usuario_logado in membros if usuario_logado else False
    usuario_e_dono = usuario_logado.nome == clube.dono if usuario_logado else False

    topicos = Topico.objects.filter(clube=clube).order_by('-criado_em')

    # 👉 aqui está o filtro de eventos ativos
    agora = timezone.now()
    eventos_ativos = clube.eventos.filter(
        Q(data_fim__isnull=True) | Q(data_fim__gt=agora)
    ).order_by('data_inicio')

    return render(request, 'chat/clubes_detalhe.html', {
        'clube': clube,
        'membros': membros,
        'moderadores': mods_list,
        'usuario_no_clube': usuario_no_clube,
        'usuario_e_dono': usuario_e_dono,
        'topicos': topicos,
        'usuario_logado': usuario_logado,
        'eventos': eventos_ativos,  # 👈 adicione isso
    })



def clubes_criar(request):
    usuario_id = request.session.get('usuario_id')
    usuario_logado = get_object_or_404(Usuario, id=usuario_id)

    if request.method == 'POST':
        form = ClubeForm(request.POST)
        if form.is_valid():
            clube = form.save(commit=False)
            clube.dono = usuario_logado.nome
            clube.save()
            usuario_logado.clubes.add(clube)
            return redirect('chat:clubes_detalhe', pk=clube.pk)
    else:
        form = ClubeForm()

    return render(request, 'chat/clubes_form.html', {'form': form, 'acao': 'Criar'})


def clubes_editar(request, pk):
    usuario_id = request.session.get('usuario_id')
    usuario_logado = get_object_or_404(Usuario, id=usuario_id)

    clube = get_object_or_404(Clube, pk=pk)
    mods_list = [mod.strip() for mod in clube.mods.split(',')] if clube.mods else []

    if usuario_logado.nome != clube.dono and usuario_logado.nome not in mods_list:
        return redirect('chat:clubes_detalhe', pk=pk)

    if request.method == 'POST':
        form = ClubeForm(request.POST, instance=clube)
        if form.is_valid():
            form.save()
            return redirect('chat:clubes_detalhe', pk=pk)
    else:
        form = ClubeForm(instance=clube)

    return render(request, 'chat/clubes_form.html', {'form': form, 'acao': 'Editar'})

@require_POST
def clubes_entrar(request, pk):
    usuario_id = request.session.get('usuario_id')
    usuario_logado = get_object_or_404(Usuario, id=usuario_id)
    clube = get_object_or_404(Clube, pk=pk)

    # Já está no clube
    if usuario_logado.clubes.filter(id=clube.id).exists():
        return redirect('chat:clubes_detalhe', pk=clube.id)

    if clube.tipo == 'Pública':
        usuario_logado.clubes.add(clube)

    elif clube.tipo == 'Privada':
        # Remove qualquer solicitação antiga desse usuário
        SolicitacaoClube.objects.filter(
            clube=clube,
            usuario_nome=usuario_logado.nome
        ).delete()

        # Cria nova solicitação com a foto
        SolicitacaoClube.objects.create(
            clube=clube,
            usuario_nome=usuario_logado.nome,
            foto_url=usuario_logado.foto  # <-- Adiciona isso
        )


    elif clube.tipo == 'Fechada':
        # Só com convite manual — não faz nada
        pass

    return redirect('chat:clubes_detalhe', pk=clube.id)




@require_POST
def clubes_sair(request, pk):
    usuario_id = request.session.get('usuario_id')
    usuario_logado = get_object_or_404(Usuario, id=usuario_id)
    clube = get_object_or_404(Clube, pk=pk)

    usuario_logado.clubes.remove(clube)
    return redirect('chat:clubes_lista')


def clube_nova_discussao(request, clube_id):
    usuario_id = request.session.get('usuario_id')
    usuario_logado = get_object_or_404(Usuario, id=usuario_id)
    arquivo = request.FILES.get('arquivo_midia')  # arquivo enviado no form
    if request.method == 'POST':
        # Supondo que você esteja criando um novo tópico
        topico = Topico.objects.create(
            titulo=request.POST.get('titulo'),
            conteudo=request.POST.get('conteudo'),
            clube_id=clube_id,
            autor=usuario_logado.nome,
            arquivo_midia=arquivo
        )
        return redirect('chat:clube_topico', clube_id=clube_id, topico_id=topico.id)

def construir_arvore_respostas(respostas):
    mapa = {}
    raiz = []

    for r in respostas:
        r.filhos = []
        mapa[r.id] = r

    for r in respostas:
        if r.resposta_pai_id:
            pai = mapa.get(r.resposta_pai_id)
            if pai:
                pai.filhos.append(r)
        else:
            raiz.append(r)
    return raiz

def clube_topico(request, clube_id, topico_id):
    clube = get_object_or_404(Clube, pk=clube_id)
    topico = get_object_or_404(Topico, pk=topico_id, clube=clube)
    usuario_id = request.session.get('usuario_id')
    usuario_logado = Usuario.objects.filter(id=usuario_id).first()
    membros = Usuario.objects.filter(clubes=clube)
    usuario_no_clube = usuario_logado in membros if usuario_logado else False

    if request.method == 'POST' and usuario_no_clube:
        conteudo = request.POST.get('comentario', '').strip()
        resposta_pai_id = request.POST.get('resposta_pai_id')
        if conteudo:
            resposta_pai = None
            if resposta_pai_id:
                try:
                    resposta_pai = Resposta.objects.get(id=resposta_pai_id, topico=topico)
                except Resposta.DoesNotExist:
                    resposta_pai = None
            Resposta.objects.create(
                topico=topico,
                autor=usuario_logado,  # Se autor é objeto Usuario, tudo certo
                conteudo=conteudo,
                resposta_pai=resposta_pai
            )
    # Query simples, sem select_related
    respostas_qs = Resposta.objects.filter(topico=topico).order_by('criado_em')
    respostas_organizadas = construir_arvore_respostas(respostas_qs)

    return render(request, 'chat/clube_topico.html', {
        'clube': clube,
        'topico': topico,
        'usuario_logado': usuario_logado,
        'usuario_no_clube': usuario_no_clube,
        'respostas_organizadas': respostas_organizadas,
    })


def criar_sala(request, clube_id):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        clube = get_object_or_404(Clube, pk=clube_id)

        if nome:
            Sala.objects.create(clube=clube, nome=nome)

    return redirect('chat:clubes_detalhe', pk=clube_id)



def sala_detalhe(request, sala_id):
    sala = get_object_or_404(Sala, pk=sala_id)
    mensagens = sala.mensagens.order_by('criado_em')[:100]

    usuario_id = request.session.get('usuario_id')
    usuario = get_object_or_404(Usuario, id=usuario_id) if usuario_id else None

    return render(request, 'chat/sala_detalhe.html', {
        'sala': sala,
        'mensagens': mensagens,
        'usuario': usuario,
    })


@csrf_exempt
def enviar_mensagem(request, sala_id):
    if request.method == "POST":
        sala = get_object_or_404(Sala, pk=sala_id)
        autor = request.POST.get('autor', 'Anônimo')
        texto = request.POST.get('texto')

        if texto:
            msg = SalaMensagem.objects.create(sala=sala, autor=autor, texto=texto)
            return JsonResponse({
                'autor': msg.autor,
                'texto': msg.texto,
                'criado_em': msg.criado_em.strftime('%H:%M')
            })
    return JsonResponse({'erro': 'Mensagem inválida'}, status=400)

def gerenciar_solicitacoes(request, pk):
    clube = get_object_or_404(Clube, pk=pk)
    usuario_id = request.session.get('usuario_id')
    usuario_logado = get_object_or_404(Usuario, id=usuario_id)

    nome_usuario = usuario_logado.nome
    mods_list = [mod.strip() for mod in clube.mods.split(',')] if clube.mods else []

    if nome_usuario != clube.dono and nome_usuario not in mods_list:
        messages.error(request, "Você não pode gerenciar este clube.")
        return redirect('chat:clubes_detalhe', pk=clube.pk)

    solicitacoes = clube.solicitacoes.filter(aprovado=False, rejeitado=False)

    if request.method == 'POST':
        acao = request.POST.get('acao')
        sol_id = request.POST.get('solicitacao_id')
        sol = get_object_or_404(SolicitacaoClube, id=sol_id, clube=clube)

        if acao == 'aprovar':
            sol.aprovado = True
            sol.save()
            usuario = Usuario.objects.filter(nome=sol.usuario_nome).first()
            if usuario:
                usuario.clubes.add(clube)
            messages.success(request, f"{sol.usuario_nome} agora faz parte do clube.")
        elif acao == 'rejeitar':
            sol.rejeitado = True
            sol.save()
            messages.info(request, f"Solicitação de {sol.usuario_nome} rejeitada.")
        return redirect('chat:gerenciar_solicitacoes', pk=clube.pk)

    return render(request, 'chat/gerenciar_solicitacoes.html', {
        'clube': clube,
        'solicitacoes': solicitacoes,
    })

def clubes_aprovar_solicitacao(request, clube_id, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoClube, id=solicitacao_id, clube_id=clube_id)
    clube = solicitacao.clube

    if request.method == 'POST':
        solicitacao.aprovado = True
        solicitacao.save()

        # adiciona o usuário como membro
        usuario = Usuario.objects.filter(nome=solicitacao.usuario_nome).first()
        if usuario:
            usuario.clubes.add(clube)

    return redirect('chat:clubes_detalhe', pk=clube_id)


def clubes_rejeitar_solicitacao(request, clube_id, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoClube, id=solicitacao_id, clube_id=clube_id)

    if request.method == 'POST':
        solicitacao.rejeitado = True
        solicitacao.save()

    return redirect('chat:clubes_detalhe', pk=clube_id)


def notificacoes(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return redirect('chat:login')

    usuario = get_object_or_404(Usuario, id=usuario_id)

    solicitacoes_raw = SolicitacaoClube.objects.filter(clube__dono=usuario.nome)

    # Junta o objeto do usuário para pegar a foto
    solicitacoes_clubes = []
    for s in solicitacoes_raw:
        try:
            u = Usuario.objects.get(nome=s.usuario_nome)
            foto = u.foto if u.foto else ''
        except Usuario.DoesNotExist:
            foto = ''
        solicitacoes_clubes.append({
            'usuario_nome': s.usuario_nome,
            'clube': s.clube,
            'foto_url': foto,
        })


    conversas_brutas = Conversation.objects \
        .filter(Q(user1=usuario) | Q(user2=usuario)) \
        .annotate(ultima_msg=Max('mensagens__timestamp')) \
        .order_by('-ultima_msg')

    conversas = []
    for conversa in conversas_brutas:
        amigo = conversa.user2 if conversa.user1 == usuario else conversa.user1
        ultima_msg = conversa.mensagens.last()
        nao_visto = (
            ultima_msg and
            ultima_msg.remetente != usuario and
            not ultima_msg.visto_por.filter(id=usuario.id).exists()
        )
        conversas.append({
            'conversa': conversa,
            'amigo': amigo,
            'nao_visto': nao_visto,
        })

    return render(request, 'chat/notificacoes.html', {
        'solicitacoes_clubes': solicitacoes_clubes,
        'conversas': conversas,
        'usuario_logado': usuario,
    })



@require_http_methods(["GET", "POST"])
def criar_evento(request, clube_id):
    usuario = get_usuario_logado(request)
    clube = get_object_or_404(Clube, pk=clube_id)

    if clube.dono != usuario.nome:
        return HttpResponseForbidden("Apenas o dono do clube pode criar eventos.")

    if request.method == 'POST':
        form = EventoForm(request.POST, request.FILES)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.clube = clube
            evento.save()
            return redirect('chat:clubes_detalhe', pk=clube.id)
    else:
        form = EventoForm()

    return render(request, 'chat/criar_evento.html', {'form': form, 'clube': clube})



@require_POST
def bloquear_usuario(request, id):
    usuario_logado = get_usuario_logado(request)  # pegue o usuário logado via sessão
    usuario_a_bloquear = get_object_or_404(Usuario, id=id)

    # Adiciona o usuário a bloquear à lista de bloqueados do usuário logado
    usuario_logado.bloqueados.add(usuario_a_bloquear)
    usuario_logado.save()

    return redirect('chat:perfil_usuario', usuario_id=usuario_a_bloquear.id)

@require_POST
def desbloquear_usuario(request, id):
    usuario_logado = get_usuario_logado(request)
    usuario_a_desbloquear = get_object_or_404(Usuario, id=id)

    usuario_logado.bloqueados.remove(usuario_a_desbloquear)
    usuario_logado.save()

    return redirect('chat:perfil_usuario', usuario_id=usuario_a_desbloquear.id)









@xframe_options_exempt
@ensure_csrf_cookie
def wplace_view(request):
    return render(request, 'chat/wplace.htm')

@xframe_options_exempt
@require_http_methods(["GET", "POST"])
def wplace_state(request):
    obj, _ = WPlaceState.objects.get_or_create(pk=1)
    if request.method == "GET":
        return JsonResponse({
            "elements": obj.elements,
            "offsetX": obj.offset_x,
            "offsetY": obj.offset_y,
            "zoom": obj.zoom,
        })
    # POST
    data = json.loads(request.body or "{}")
    if "elements" in data: obj.elements = data["elements"]
    if "offsetX" in data:  obj.offset_x = float(data["offsetX"])
    if "offsetY" in data:  obj.offset_y = float(data["offsetY"])
    if "zoom" in data:     obj.zoom = float(data["zoom"])
    obj.save()
    return JsonResponse({"ok": True})



