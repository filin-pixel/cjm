import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="CJM Generator", page_icon="🗺️", layout="wide")

# --- ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ---
if 'personas' not in st.session_state:
    st.session_state.personas = []
if 'current_idea' not in st.session_state:
    st.session_state.current_idea = ""
if 'common_scenario' not in st.session_state:
    st.session_state.common_scenario = []
if 'cjms' not in st.session_state:
    st.session_state.cjms = {}

# --- ФУНКЦИИ (ЗДЕСЬ БУДЕТ ИНТЕГРАЦИЯ С LLM) ---
def mock_generate_common_scenario(idea):
    """Заглушка для генерации общего сценария. В реальности здесь будет вызов OpenAI API."""
    return [
        "Осознание потребности",
        "Поиск и сравнение решений",
        "Регистрация / Первое касание",
        "Основное использование (Aha! moment)",
        "Возникновение вопроса / проблемы",
        "Обращение в поддержку или завершение"
    ]

def mock_generate_persona_cjm(idea, persona, scenario_stages):
    """Заглушка для генерации CJM под конкретную персону."""
    cjm_data = []
    for stage in scenario_stages:
        cjm_data.append({
            "Этап": stage,
            "Действия": f"[{persona['name']}] конкретное действие на этапе '{stage}'",
            "Мысли": f"А подойдет ли это мне? ({persona['goal']})",
            "Эмоции": "😐 3/5" if "проблем" in stage.lower() else "🙂 4/5",
            "Точки контакта": persona.get("channels", "Сайт, Приложение"),
            "Боли": persona.get("pains", "Нет явных болей"),
            "Решения": "Упростить интерфейс, добавить подсказку",
            "Метрики": "Conversion Rate, Time to Complete"
        })
    return cjm_data

def export_to_miro_csv(cjm_data, persona_name):
    """Конвертация CJM в формат, удобный для импорта в Miro (CSV)"""
    df = pd.DataFrame(cjm_data)
    # Добавляем колонку для Miro, чтобы при импорте было понятно, к какой персоне относится
    df.insert(0, "Персона", persona_name)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, sep=";") # Miro часто лучше понимает точку с запятой для RU-locale
    return csv_buffer.getvalue()

def export_to_mermaid(cjm_data, persona_name):
    """Генерация Mermaid.js кода для визуализации (можно вставить в Figma плагин)"""
    mermaid = f"---\nconfig:\n  theme: base\n---\njourney\n  title CJM: {persona_name}\n"
    for row in cjm_data:
        # Оцениваем эмоцию для Mermaid (извлекаем число из строки типа "🙂 4/5")
        score = 3
        if "5/5" in row["Эмоции"] or "😍" in row["Эмоции"]: score = 5
        elif "4/5" in row["Эмоции"] or "🙂" in row["Эмоции"]: score = 4
        elif "2/5" in row["Эмоции"] or "😕" in row["Эмоции"]: score = 2
        elif "1/5" in row["Эмоции"] or "😡" in row["Эмоции"]: score = 1
        
        action = row["Действия"].replace('"', "'")
        mermaid += f'  section {row["Этап"]}\n    {action}: {score}: {persona_name}\n'
    return mermaid

# --- ИНТЕРФЕЙС: БОКОВАЯ ПАНЕЛЬ (УПРАВЛЕНИЕ ПЕРСОНАМИ) ---
with st.sidebar:
    st.header("👥 Профили (Персоны)")
    
    with st.expander("➕ Добавить новую персону"):
        with st.form("add_persona_form"):
            p_name = st.text_input("Имя профиля *", placeholder="Напр: Новичок Иван")
            p_role = st.text_input("Роль / Контекст *", placeholder="Напр: Первый раз ищет услугу")
            p_goal = st.text_input("Главная цель *", placeholder="Напр: Быстро оформить заказ")
            
            st.markdown("**Опционально:**")
            p_tech = st.selectbox("Техн. грамотность", ["Низкая", "Средняя", "Высокая"])
            p_pains = st.text_area("Ключевые боли / Страхи", placeholder="Боится скрытых платежей")
            p_channels = st.text_input("Любимые каналы", placeholder="Telegram, Мобильное приложение")
            
            submitted = st.form_submit_button("Сохранить профиль")
            if submitted and p_name and p_role and p_goal:
                new_persona = {
                    "name": p_name, "role": p_role, "goal": p_goal,
                    "tech": p_tech, "pains": p_pains, "channels": p_channels
                }
                st.session_state.personas.append(new_persona)
                st.success(f"Профиль '{p_name}' добавлен!")
                st.rerun()

    if st.session_state.personas:
        st.markdown("---")
        for i, p in enumerate(st.session_state.personas):
            st.markdown(f"**{p['name']}**\n*{p['role']}*")
            if st.button(f"🗑️ Удалить {p['name']}", key=f"del_{i}"):
                st.session_state.personas.pop(i)
                st.rerun()
    else:
        st.info("Добавьте хотя бы одну персону для начала работы.")

# --- ИНТЕРФЕЙС: ОСНОВНАЯ ЧАСТЬ ---
st.title("🗺️ Генератор Customer Journey Map")
st.markdown("Введите идею, получите общий сценарий и адаптируйте его под выбранные профили.")

idea = st.text_area("💡 Ваша новая идея или задача:", height=100, placeholder="Например: Мобильное приложение для выгула собак по подписке в Москве")

col1, col2 = st.columns([1, 1])

with col1:
    if st.button("🧠 1. Предложить общий сценарий", use_container_width=True):
        if idea:
            st.session_state.current_idea = idea
            st.session_state.common_scenario = mock_generate_common_scenario(idea)
            st.success("Общий сценарий сгенерирован! Переходите к шагу 2.")
        else:
            st.warning("Сначала введите идею.")

with col2:
    if st.session_state.common_scenario and st.session_state.personas:
        st.markdown("**Выберите профили для детализации:**")
        selected_personas = []
        for p in st.session_state.personas:
            if st.checkbox(p['name'], value=True):
                selected_personas.append(p)
        
        if st.button("🚀 2. Построить CJM для выбранных профилей", use_container_width=True, type="primary"):
            for p in selected_personas:
                st.session_state.cjms[p['name']] = mock_generate_persona_cjm(idea, p, st.session_state.common_scenario)
            st.success("CJM успешно построены! Прокрутите вниз.")

# --- ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ ---
if st.session_state.cjms:
    st.markdown("---")
    st.subheader("📊 Результаты CJM")
    
    tabs = st.tabs([f"👤 {name}" for name in st.session_state.cjms.keys()] + ["📥 Экспорт"])
    
    for i, (name, cjm_data) in enumerate(st.session_state.cjms.items()):
        with tabs[i]:
            st.markdown(f"### Профиль: {name}")
            df = pd.DataFrame(cjm_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("**Код для Figma (Mermaid.js):**")
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
