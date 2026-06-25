import rdetoolkit

from modules_eis import datasets_process

rdetoolkit.workflows.run(custom_dataset_function=datasets_process.dataset)
