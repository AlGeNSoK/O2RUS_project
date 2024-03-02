import fitz
import re
import os
from dotenv import load_dotenv
from models import Parameters, create_tables
import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker


def read_pdf_file(pdf):
    """
    Чтение pdf-файла в список
    """
    doc = fitz.open(pdf)
    extracted_text = []
    for page_num in range(doc.page_count):
        page = doc[page_num]
        extracted_text.append(page.get_text().split('\n'))
    doc.close()
    doc_list = []
    for page in extracted_text:
        doc_list.extend(page[3:])

    return doc_list


def save_data_db(session):
    """
    Запись информации в базу данных
    """
    global parameter
    for parameter in full_parameter_list:
        for table_param in parameter.get('Table Parameter'):
            for param in paragraph_52_list:
                if (param.get('Paragraph') in table_param.get('Parameter Paragraph')
                        and param.get('Parameter Name') in table_param.get('Parameter Name')):
                    session.add(Parameters(ID=parameter.get('ID'), Data_Length=parameter.get('Data Length'),
                                           Length=table_param.get('Length'), Name=table_param.get('Parameter Name'),
                                           Scaling=param.get('Slot Scaling'), Range=param.get('Slot Range'),
                                           SPN=param.get('SPN')))
    session.commit()


if __name__ == '__main__':
    pdf_document = 'SAE J1939-71.pdf'
    document_list = read_pdf_file(pdf_document)

    doc_index = '-71'
    pattern = r"5.3.\d\d?\d?[?]?[?]?"
    pattern_pp = r"5\.2\.\d\.[?]{0,3}\d{0,3}"
    paragraph_52_flag = False
    slot_scaling_flag = False
    slot_range_flag = False
    spn_flag = False
    paragraph_flag = False
    data_length_flag = False
    pgn_flag = False
    id_flag = False
    table_flag = False
    table_start_flag = False
    paragraph_52_list = []
    full_parameter_list = []

    i = 0
    while i < len(document_list):

        # Заполнение списка словарей данными из параграфа 5.2
        match_pp = re.search(pattern_pp, document_list[i])
        if match_pp is not None and doc_index in document_list[i - 1]:
            paragraph_52 = match_pp[0]
            paragraph_52_flag = True
            parameter_name_52 = document_list[i + 1].strip()
        if 'Slot Scaling:' in document_list[i]:
            slot_scaling = document_list[i].split(':')[1].strip()
            slot_scaling_flag = True
        if 'Slot Range:' in document_list[i]:
            slot_range = document_list[i + 1].strip()
            slot_range_flag = True
        if 'SPN:' in document_list[i]:
            spn = document_list[i + 1].strip()
            spn_flag = True

        # Если заполнены все переменные, то создаем словарь и добавляем его к общему списку
        if paragraph_52_flag and slot_scaling_flag and slot_range_flag and spn_flag:
            parameter_52 = {'Paragraph': paragraph_52, 'Parameter Name': parameter_name_52,
                            'Slot Scaling': slot_scaling,
                            'Slot Range': slot_range, 'SPN': spn}
            paragraph_52_list.append(parameter_52)
            paragraph_52_flag = False
            slot_scaling_flag = False
            slot_range_flag = False
            spn_flag = False
            i += 1
            continue

        # Заполнение списка словарей данными из параграфа 5.3
        match = re.search(pattern, document_list[i])
        if match is not None:
            if match[0] in document_list[i] and doc_index in document_list[i - 1]:
                paragraph = match[0]
                paragraph_flag = True
        if 'Data Length:' in document_list[i]:
            data_length = document_list[i].strip()
            data_length_values = document_list[i + 1].strip()
            data_length_flag = True
        if 'Parameter Group' in document_list[i]:
            pgn = document_list[i + 1].strip()
            id_ = ''.join(document_list[(i + 2):(i + 4)]).strip().lstrip('(').rstrip(')').strip()
            pgn_flag = True
            id_flag = True
        # Заполнение списка словарей данными из таблиц в параграфах 5.3
        if 'POS' in document_list[i] and 'Length' in document_list[i + 1] and 'Parameter Name' in document_list[i + 2]:
            if i + 5 < len(document_list):
                i = i + 5
            parameter_list = []
            while i + 5 < len(document_list):
                parameter = {}
                pattern2 = r"\d\.?[,]?\d?"
                match2 = re.search(pattern2, document_list[i])
                if match2 is None:
                    i += 1
                pattern_l = r"\d\sb[i,y]t[s,e][s]?"
                length = ""
                j = i
                while j < i + 5:
                    match_l = re.search(pattern_l, document_list[j])
                    match_pp = re.search(pattern_pp, document_list[j])
                    if match_l is not None:
                        length = document_list[j].strip()
                    elif not length:
                        length = ""
                    if match_pp is not None:
                        paragraph_find = document_list[j].strip()
                        parameter_name = document_list[j - 2].strip()
                    else:
                        paragraph_find = None
                        parameter_name = None
                    if paragraph_find is not None:
                        parameter['Length'] = length
                        parameter['Parameter Name'] = parameter_name
                        parameter['Parameter Paragraph'] = paragraph_find
                        parameter_list.append(parameter)
                    j += 1
                # Определение окончания таблицы в параграфе 5.3
                if i + 8 >= len(document_list):
                    table_flag = True
                    break
                else:
                    i += 6
                    if (doc_index in document_list[i]
                            or doc_index in document_list[i + 1]
                            or doc_index in document_list[i + 2]
                            or doc_index in document_list[i - 1]
                            or doc_index in document_list[i - 2]):
                        table_flag = True
                        i = i - 1
                        break

        if paragraph_flag and data_length_flag and pgn_flag and id_flag and table_flag:
            parameter_dict = {'Paragraph': paragraph, 'Data Length': data_length_values, 'PGN': pgn, 'ID': id_,
                              'Table Parameter': parameter_list}
            full_parameter_list.append(parameter_dict)
            paragraph_flag = False
            data_length_flag = False
            pgn_flag = False
            id_flag = False
            table_flag = False

        i += 1

    load_dotenv()
    DSN = os.getenv("DSN")

    engine = sq.create_engine(DSN)
    create_tables(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    save_data_db(session)

    session.close()
