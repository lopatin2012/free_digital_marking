# app_true_api/helpers/helper_signature.py

import base64
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import pythoncom
import win32com.client

logger = logging.getLogger(__name__)


@contextmanager
def com_initialized():
    """Безопасная работа с COM"""
    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


class CadesSigner:
    """Создание подписей через КриптоПро (CAdESCOM)"""

    # Константы CAdESCOM
    CURRENT_USER_STORE = 2
    MY_STORE = 'My'
    MAXIMUM_ALLOWED = 2
    BASE64_TO_BINARY = 1
    CADES_BES = 1
    ENCODE_BASE64 = 0

    def __init__(self, serial_number: str):
        self.serial_number = serial_number.upper()

    def _find_certificate(self, store) -> Optional[object]:
        """Ищет сертификат по серийному номеру"""
        for cert in store.Certificates:

            if cert.SerialNumber.upper() == self.serial_number:
                return cert

        return None

    def _prepare_signer(self, cert):
        """Настраивает объект подписчика с атрибутом времени"""
        signer = win32com.client.Dispatch('CAdESCOM.CPSigner')
        signer.Certificate = cert

        # Добавляем атрибут времени подписи
        time_attr = win32com.client.Dispatch('CAdESCOM.CPAttribute')
        time_attr.Name = 0  # SIGNING_TIME
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

        with com_initialized():
            try:
                store = win32com.client.Dispatch('CAdESCOM.Store')
                store.Open(self.CURRENT_USER_STORE, self.MY_STORE, self.MAXIMUM_ALLOWED)

                try:
                    cert = self._find_certificate(store)
                    if not cert:
                        raise ValueError(f'Сертификат {self.serial_number} не найден в хранилище')

                    signer = self._prepare_signer(cert)

                    signed_data = win32com.client.Dispatch('CAdESCOM.CadesSignedData')
                    signed_data.ContentEncoding = self.BASE64_TO_BINARY
                    signed_data.Content = self._encode_content(data)

                    signature = signed_data.SignCades(
                        signer,
                        self.CADES_BES,
                        is_detached,
                        self.ENCODE_BASE64
                    )

                    result = data, self._clean_signature(signature)
                    logger.debug("Подпись успешно создана")
                    return result

                finally:
                    store.Close()

            except Exception as e:
                logger.error(f"Ошибка при создании подписи: {e}")
                raise
