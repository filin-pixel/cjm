import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
import openai

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

# --- ФУНКЦИИ ГЕНЕРАЦИИ (REAL LLM) ---
def get_llm_client(api_key):
    return openai.OpenAI(api_key=api_key)

def generate_common_scenario(idea, api_key):
    client = get_llm_client(api_key)
    prompt = f"""
    Ты — опытный продуктовый аналитик. 
    Идея продукта: "{idea}"
    
    Предложи общий сценарий Customer Journey из 5-6 этапов для этой идеи.
    Верни ответ СТРОГО в формате JSON-массива строк. Пример:
    ["Осознание потребности", "Изучение продукта", "Настройка", "Первое использование", "Регулярное использование", "Вывод средств"]
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # или gpt-3.5-turbo, или другая доступная модель
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        # Извлекаем массив из JSON {"scenario": ["этап1", "этап2"]}
        # Мы попросим модель вернуть ключ "stages"
        data = json.loads(response.choices[0].message.content)
        # Обработка на случай, если модель вернула просто массив или объект
        if isinstance(data, list):
            return data
        elif "stages" in data:
            return data["stages"]
        elif "scenario" in data:
            return data["scenario"]
        else:
            return list(data.values())[0] # fallback
    except Exception as e:
        st.error(f"Ошибка генерации сценария: {e}")
        return []

def generate_persona_cjm(idea, persona, scenario_stages, api_key):
    client = get_llm_client(api_key)
    
    persona_desc = f"Имя: {persona['name']}. Роль: {persona['role']}. Цель: {persona['goal']}. Боли: {persona.get('pains', 'Не указаны')}. Каналы: {persona.get('channels', 'Не указаны')}."
    
    prompt = f"""
    Ты — опытный продуктовый аналитик и UX-исследователь.
    Идея продукта: "{idea}"
    Персона: {persona_desc}
    Этапы сценария: {", ".join(scenario_stages)}

    Сгенерируй Customer Journey Map (CJM) для этой персоны по указанным этапам.
    Верни ответ СТРОГО в формате JSON-массива объектов. Каждый объект должен содержать ровно эти ключи:
    "Этап", "Действия", "Мысли", "Эмоции" (формат: "Эмодзи X/5 (Краткое описание)"), 
    "Точки контакта", "Боли", "Решения", "Метрики".
    
    Пример формата:
    [
      {{
        "Этап": "Осознание потребности",
        "Действия": "Видит баннер в приложении",
        "Мысли": "А это безопасно?",
        "Эмоции": "😐 2/5 (Недоверие)",
        "Точки контакта": "Главный экран, Push",
        "Боли": "Страх скрытых комиссий",
        "Решения": "Добавить плашку 'Без комиссий'",
        "Метрики": "CTR баннера"
      }}
    ]
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        data = json.loads(response.choices[0].message.content)
        
        # Извлекаем массив, независимо от того, как модель его назвала (cjm, stages, data и т.д.)
        if isinstance(data, list):
            return data
        else:
            # Ищем первый ключ, который является списком
            for key, value in data.items():
                if isinstance(value, list):
                    return value
            return [] # fallback
            
    except Exception as e:
        st.error(f"Ошибка генерации CJM для {persona['name']}: {e}")
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
    
    api_key = st.text_input("🔑 OpenAI API Key", type="password", help="Введите ваш ключ для генерации")
    
    st.markdown("---")
    st.subheader("👥 Профили (Персоны)")
    
    with st.expander("➕ Добавить новую персону"):
        with st.form("add_persona_form"):
            p_name = st.text_input("Имя профиля *", placeholder="Напр: Осторожный Олег")
            p_role = st.text_input("Роль / Контекст *", placeholder="Напр: Зарплатный клиент, боится рисков")
            p_goal = st.text_input("Главная цель *", placeholder="Напр: Сохранить деньги без потерь")
            
            st.markdown("**Опционально:**")
            p_pains = st.text_area("Ключевые боли / Страхи", placeholder="Боится скрытых комиссий и сложных терминов")
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
st.markdown("Введите идею, получите общий сценарий и адаптируйте его под выбранные профили с помощью AI.")

idea = st.text_area("💡 Ваша новая идея или задача:", height=100, 
                    placeholder="Например: Сервис 'Инвесткопилка' на базе БПИФ Ликвидный (SCLI) с механиками автопополнения и округления трат.")

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🧠 1. Предложить общий сценарий (AI)", use_container_width=True):
        if not api_key:
            st.warning("Пожалуйста, введите OpenAI API Key в боковой панели.")
        elif idea:
            with st.spinner("Нейросеть анализирует идею и строит сценарий..."):
                st.session_state.current_idea = idea
                st.session_state.common_scenario = generate_common_scenario(idea, api_key)
                if st.session_state.common_scenario:
                    st.success("Общий сценарий сгенерирован! Переходите к шагу 2.")
                else:
                    st.error("Не удалось сгенерировать сценарий. Проверьте API ключ.")
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
            if not api_key:
                st.warning("Пожалуйста, введите OpenAI API Key в боковой панели.")
            else:
                with st.spinner("Нейросеть генерирует CJM для каждого профиля... Это может занять 10-20 секунд."):
                    for p in selected_personas:
                        cjm = generate_persona_cjm(idea, p, st.session_state.common_scenario, api_key)
                        if cjm:
                            st.session_state.cjms[p['name']] = cjm
                    st.success("CJM успешно построены! Прокрутите вниз.")

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
