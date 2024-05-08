import asyncio
import uuid

from domika.database.core import AsyncSessionFactory
from domika.device import service as device_service
from domika.device.models import Device, DomikaDeviceCreate


async def amain():
    async with AsyncSessionFactory() as session:
        await device_service.create(
            session,
            DomikaDeviceCreate(
                "app_id",
                uuid.uuid4(),
                "token",
                "ios",
                "env",
            ),
        )


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
