import base64
import logging
from datetime import datetime

import pycades

logger = logging.getLogger(__name__)


class CadesSigner:
    """Создание подписей через КриптоПро (pycades)"""

    def __init__(self, serial_number: str):
        self.serial_number = serial_number.upper()

    def _find_certificate(self) -> pycades.Certificate:
        """Ищет сертификат по серийному номеру в хранилищеCurrentUser\\My"""
        store = pycades.Store()
        store.Open(
            pycades.CAPICOM_CURRENT_USER_STORE,
            pycades.CAPICOM_MY_STORE,
            pycades.CAPICOM_STORE_OPEN_MAXIMUM_ALLOWED
        )

        # Ищем сертификат по серийному номеру
        certs = store.Certificates.Find(
            pycades.CERTIFICATE_FIND_BY_SERIAL_NUMBER,
            self.serial_number
        )

        if certs.Count == 0:
            raise ValueError(f'Сертификат {self.serial_number} не найден в хранилище')

        return certs.Item(1)  # pycades использует 1-based индексацию

    def _prepare_signer(self, cert: pycades.Certificate) -> pycades.CPSigner:
        """Настраивает объект подписчика с атрибутом времени"""
        signer = pycades.CPSigner()
        signer.Certificate = cert

        # Добавляем атрибут времени подписи
        time_attr = pycades.CPAttribute()
        time_attr.Name = pycades.CAPICOM_AUTHENTICATED_ATTRIBUTE_SIGNING_TIME # Атрибут времени
        time_attr.Value = datetime.now()
        signer.AuthenticatedAttributes2.Add(time_attr)

        return signer

    def _encode_content(self, data: str) -> str:
        """Кодирует данные в base64"""
        return base64.b64encode(data.encode('utf-8')).decode('ascii')

    def _clean_signature(self, signature: str) -> str:
        """Удаляет переносы строк из base64-подписи"""
        return signature.replace('\r', '').replace('\n', '')

    def sign_data(self, data: str, is_detached: bool = False) -> tuple[str, str]:
        """Создаёт ЭЦП для данных.

        :param data: Данные для подписи
        :param is_detached: True - откреплённая подпись, False - прикреплённая
        :return: (исходные_данные, подпись)
        """
        logger.debug(f"Подписание данных (откреплённая={is_detached}), сертификат: {self.serial_number}")

        try:
            # Находим сертификат
            cert = self._find_certificate()

            # Настраиваем подписчика
            signer = self._prepare_signer(cert)

            # Создаём объект подписанных данных
            signed_data = pycades.CadesSignedData()
            signed_data.ContentEncoding = pycades.CADESCOM_BASE64_TO_BINARY # Кодирование контента
            signed_data.Content = self._encode_content(data)

            # Подписываем
            signature = signed_data.SignCades(
                signer,
                pycades.CADESCOM_CADES_BES, # Тип подписи
                is_detached
            )

            result = data, self._clean_signature(signature)
            logger.info('Подпись успешно создана')
            return result

        except Exception as e:
            logger.error(f'Ошибка при создании подписи: {e}')
            raise
