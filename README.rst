============================================
Gestione Agenti, Salesmen Management, rel.10
============================================

------------------
Note Installazione
------------------

Per problemi legati alla dipendenza tra i moduli il profilo agente è definito in cq_sales_10, mentre tutte le sue regole di accesso sono definite qui.
Alcune regole di accesso e permessi per i punti di menu sono stati aggiunti nei moduli l10n_it_ddt e stock_picking_package_preparation.
Tutto questo per poter slegare questo modulo ai moduli dei DDT, e poter installare o solo gli agenti, o solo il DDT, o entrambi, a seconda delle esigenze dei clienti.

Per la creazione di un nuovo agente:
------------------------------------
* durante la creazione togliere tutti i gruppi/flag impostati di default
* flaggare solamente agente
* salvare, verrà aggiunto il gruppo portale
* andare sul partner collegato
* flaggare è un fornitore ed è un agente

Installazione Enasarco
----------------------

* Flaggare enasarco in Vendite --> Configurazione --> Enasarco
* Inserire il "Conto di costo" e l'imposta per il fornitore nei prodotti "Quota Enasarco", "Fisso Agente" e "Provvigioni Agente" creati dal modulo all'installazione
    - Il "Conto di costo" è a discrezione del cliente
    - L'aliquota per "Fisso Agente" e "Provvigioni Agente" dovrebbe essere la normale 22a, mentre per "Quota Enasarco" andrebbe creata un'aliquota nulla che non dovrebbe venire  stampata nè nel registro IVA, nè nella liquidazione IVA nè in ogni altra dichiarazione
* Creare una ritenuta per le provvigioni in Contabilità --> Configurazione --> Contabilità --> Ritenuta
    - Inserire i conti standard per le ritenute
    - Inserire il termine di pagamento '15 del mese successivo', se necessario crearlo
    - Inserire una riga con il 23% di ritenuta e 0.5 coefficiente imponibile
* Creare una posizione fiscale agente inserendo la ritenuta creata e associarla ai vari partner agenti.
* La configurazione in Contabilità --> Configurazione --> Contabilità --> Enasarco dovrebbe essere compilata dal cliente, così come i mandati sulla scheda dell'agente.

Per ulteriori informazioni sul funzionamento del modulo vedere il documento nei progetti generici di drive.
