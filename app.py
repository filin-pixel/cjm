import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="CJM Generator Pro", page_icon="🗺️", layout="wide")

# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if 'personas' not in st.session_state:
    st.session_state.personas = []
if 'current_idea' not in st.session_state:
    st.session_state.current_idea = ""
if 'common_scenario' not in st.session_state:
    st.session_state.common_scenario = []
if 'cjms' not in st.session_state:
    st.session_state.cjms = {}

# --- ФУНКЦИИ ГЕНЕРАЦИИ (GigaChat) ---
def get_giga_client(credentials):
    return GigaChat(
        credentials=credentials,
        scope="GIGACHAT_API_PERS",  # Для физлиц. Для юрлиц: GIGACHAT_API_CORP
        model="GigaChat",            # Или "GigaChat-Pro" для более сложных задач
        verify_ssl_certs=False       # Отключаем проверку SSL для простоты
    )

def call_gigachat(client, prompt, max_tokens=2000):
    """Универсальная функция вызова GigaChat с улучшенным парсингом JSON"""
    try:
        # Параметры max_tokens и temperature передаются в объект Chat, а не в метод chat()
        response = client.chat(
            Chat(
                messages=[Messages(role=MessagesRole.USER, content=prompt)],
                max_tokens=max_tokens,
                temperature=0.3
            )
        )
        content = response.choices[0].message.content
        
        # Очищаем от markdown-оберток
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        content = content.strip()
        
        # Пытаемся распарсить
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ JSON поврежден, пытаюсь восстановить... Ошибка: {e}")
            
            # Пробуем найти начало и конец JSON
            if content.startswith("{") or content.startswith("["):
                # Ищем последнюю закрывающую скобку
                if content.startswith("{"):
                    # Ищем последнюю }
                    last_brace = content.rfind("}")
                    if last_brace > 0:
                        content = content[:last_brace+1]
                elif content.startswith("["):
                    last_bracket = content.rfind("]")
                    if last_bracket > 0:
                        content = content[:last_bracket+1]
                
                try:
                    return json.loads(content)
                except:
                    pass
            
            # Если не получилось, показываем что получили
            st.error("Не удалось восстановить JSON. Полученный ответ:")
            st.code(content[:1000])
            return None
            
    except Exception as e:
        st.error(f"Ошибка вызова GigaChat: {e}")
        return None

def generate_common_scenario(idea, credentials):
    client = get_giga_client(credentials)
    prompt = f"""
Ты — опытный продуктовый аналитик.
Идея продукта: "{idea}"

Предложи общий сценарий Customer Journey из 5-6 этапов для этой идеи.

Верни ответ СТРОГО в формате JSON без лишнего текста:
{{"stages": ["Этап 1", "Этап 2", "Этап 3", "Этап 4", "Этап 5"]}}

Будь лаконичен в названиях этапов (3-5 слов максимум).
"""
    data = call_gigachat(client, prompt, max_tokens=500)
    if not data:
        return []
    if isinstance(data, list):
        return data
    for key in ["stages", "scenario", "этапы", "stages_names"]:
        if key in data:
            return data[key]
    return list(data.values())[0] if data else []

def generate_persona_cjm(idea, persona, scenario_stages, credentials):
    client = get_giga_client(credentials)
    
    persona_desc = f"Имя: {persona['name']}. Роль: {persona['role']}. Цель: {persona['goal']}."
    if persona.get('pains'):
        persona_desc += f" Боли: {persona['pains']}."
    
    stages_str = ", ".join(scenario_stages)
    
    prompt = f"""
Ты — опытный продуктовый аналитик и UX-исследователь.
Идея: "{idea}"
Персона: {persona_desc}
Этапы: {stages_str}

Сгенерируй CJM. Верни СТРОГО JSON:
{{"cjm": [
  {{"Этап": "Название", "Действия": "текст", "Мысли": "текст", "Эмоции": "🙂 4/5 (описание)", "Точки контакта": "каналы", "Боли": "проблемы", "Решения": "гипотезы", "Метрики": "метрики"}}
]}}

Правила:
1. Будь лаконичен (каждое поле 5-15 слов)
2. Используй только указанные ключи
3. Никакого текста вне JSON
4. Закрой все скобки в конце
"""
    data = call_gigachat(client, prompt, max_tokens=2500)
    if not data:
        return []
    if isinstance(data, list):
        return data
    for key in ["cjm", "data", "stages", "result", "cjms"]:
        if key in data and isinstance(data[key], list):
            return data[key]
    return []
    
# --- ФУНКЦИИ ЭКСПОРТА ---
def export_to_miro_csv(cjm_data, persona_name):
    df = pd.DataFrame(cjm_data)
    df.insert(0, "Персона", persona_name)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, sep=";")
    return csv_buffer.getvalue()

def export_to_mermaid(cjm_data, persona_name):
    mermaid = f"---\nconfig:\n  theme: base\n---\njourney\n  title CJM: {persona_name}\n"
    for row in cjm_data:
        score = 3
        emotion_str = str(row.get("Эмоции", "3/5"))
        if "5/5" in emotion_str or "😍" in emotion_str: score = 5
        elif "4/5" in emotion_str or "🙂" in emotion_str or "😊" in emotion_str: score = 4
        elif "2/5" in emotion_str or "😕" in emotion_str: score = 2
        elif "1/5" in emotion_str or "😡" in emotion_str: score = 1
        
        action = str(row.get("Действия", "Действие")).replace('"', "'")
        stage = str(row.get("Этап", "Этап")).replace('"', "'")
        mermaid += f'  section {stage}\n    {action}: {score}: {persona_name}\n'
    return mermaid

# --- ИНТЕРФЕЙС: БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Настройки и Профили")
    
    credentials = st.text_input(
        "🔑 GigaChat Credentials", 
        type="password", 
        help="Скопируй из личного кабинета developers.sber.ru"
    )
    
    st.markdown("---")
    st.subheader("👥 Профили (Персоны)")
    
    with st.expander("➕ Добавить новую персону"):
        with st.form("add_persona_form"):
            p_name = st.text_input("Имя профиля *", placeholder="Напр: Осторожный Олег")
            p_role = st.text_input("Роль / Контекст *", placeholder="Напр: Зарплатный клиент, боится рисков")
            p_goal = st.text_input("Главная цель *", placeholder="Напр: Сохранить деньги без потерь")
            
            st.markdown("**Опционально:**")
            p_pains = st.text_area("Ключевые боли / Страхи", placeholder="Боится скрытых комиссий")
            p_channels = st.text_input("Любимые каналы", placeholder="Мобильное приложение, Push")
            
            submitted = st.form_submit_button("Сохранить профиль")
            if submitted and p_name and p_role and p_goal:
                new_persona = {
                    "name": p_name, "role": p_role, "goal": p_goal,
                    "pains": p_pains, "channels": p_channels
                }
                st.session_state.personas.append(new_persona)
                st.success(f"Профиль '{p_name}' добавлен!")
                st.rerun()

    if st.session_state.personas:
        st.markdown("---")
        for i, p in enumerate(st.session_state.personas):
            st.markdown(f"**{p['name']}**\n*{p['role']}*")
            if st.button(f"🗑️ Удалить", key=f"del_{i}"):
                st.session_state.personas.pop(i)
                st.rerun()
    else:
        st.info("Добавьте хотя бы одну персону.")

# --- ИНТЕРФЕЙС: ОСНОВНАЯ ЧАСТЬ ---
st.title("🗺️ Генератор Customer Journey Map")
st.markdown("Введите идею, получите общий сценарий и адаптируйте его под выбранные профили с помощью GigaChat AI.")

idea = st.text_area("💡 Ваша новая идея или задача:", height=100, 
                    placeholder="Например: Сервис 'Инвесткопилка' на базе БПИФ Ликвидный (SCLI) с механиками автопополнения и округления трат.")

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🧠 1. Предложить общий сценарий (AI)", use_container_width=True):
        if not credentials:
            st.warning("Пожалуйста, введите GigaChat Credentials в боковой панели.")
        elif idea:
            with st.spinner("Нейросеть анализирует идею и строит сценарий..."):
                st.session_state.current_idea = idea
                st.session_state.common_scenario = generate_common_scenario(idea, credentials)
                if st.session_state.common_scenario:
                    st.success("Общий сценарий сгенерирован! Переходите к шагу 2.")
                else:
                    st.error("Не удалось сгенерировать сценарий. Проверьте ключ и попробуйте снова.")
        else:
            st.warning("Сначала введите идею.")

with col2:
    if st.session_state.common_scenario and st.session_state.personas:
        st.markdown("**✅ Сценарий готов. Выберите профили для детализации:**")
        selected_personas = []
        for p in st.session_state.personas:
            if st.checkbox(p['name'], value=True):
                selected_personas.append(p)
        
        if st.button("🚀 2. Построить CJM для выбранных профилей (AI)", use_container_width=True, type="primary"):
            if not credentials:
                st.warning("Пожалуйста, введите GigaChat Credentials в боковой панели.")
            else:
                with st.spinner("Нейросеть генерирует CJM для каждого профиля... Это может занять 10-30 секунд."):
                    for p in selected_personas:
                        cjm = generate_persona_cjm(idea, p, st.session_state.common_scenario, credentials)
                        if cjm:
                            st.session_state.cjms[p['name']] = cjm
                    if st.session_state.cjms:
                        st.success("CJM успешно построены! Прокрутите вниз.")
                    else:
                        st.error("Не удалось сгенерировать CJM. Проверьте ключ.")

# --- ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ ---
if st.session_state.cjms:
    st.markdown("---")
    st.subheader("📊 Результаты CJM")
    
    tab_names = [f"👤 {name}" for name in st.session_state.cjms.keys()] + ["📥 Экспорт в Miro/Figma"]
    tabs = st.tabs(tab_names)
    
    for i, (name, cjm_data) in enumerate(st.session_state.cjms.items()):
        with tabs[i]:
            st.markdown(f"### Профиль: {name}")
            df = pd.DataFrame(cjm_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            with st.expander("Показать код для Figma (Mermaid.js)"):
                mermaid_code = export_to_mermaid(cjm_data, name)
                st.code(mermaid_code, language="mermaid")
                st.caption("Скопируйте этот код и вставьте в Figma через плагин 'Mermaid Figma' или 'Auto Layout Table'.")

    with tabs[-1]:
        st.subheader("📥 Выгрузка данных")
        st.markdown("Выберите профиль для выгрузки в Miro (CSV):")
        export_persona = st.selectbox("Профиль", list(st.session_state.cjms.keys()))
        
        if st.button("Скачать CSV для Miro"):
            csv_data = export_to_miro_csv(st.session_state.cjms[export_persona], export_persona)
            st.download_button(
                label="⬇️ Скачать .csv",
                data=csv_data,
                file_name=f"CJM_{export_persona}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            st.info("💡 **Как импортировать в Miro:** Создайте новую доску -> Нажмите на иконку '+' слева или 'Import' -> Выберите 'CSV'. Загрузите файл, и Miro создаст карточки или таблицу.")
